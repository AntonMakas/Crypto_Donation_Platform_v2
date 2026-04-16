// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

contract JarFund {
    enum JarStatus {
        Active,
        Completed,
        Expired,
        Withdrawn
    }

    struct Jar {
        uint256 id;
        address creator;
        string title;
        string description;
        uint256 targetAmount;
        uint256 amountRaised;
        uint256 deadline;
        JarStatus status;
        uint256 donorCount;
        uint256 createdAt;
    }

    uint256 public constant MIN_TARGET = 0.01 ether;
    uint256 public constant MIN_DONATION = 0.001 ether;
    uint256 public constant MIN_DURATION = 1 hours;
    uint256 public constant MAX_DURATION = 365 days;
    uint256 public constant MAX_PLATFORM_FEE_BPS = 1_000;

    uint256 public totalJars;
    uint256 public platformFeeBps;
    uint256 public accumulatedFees;
    address public owner;

    mapping(uint256 => Jar) private jars;
    mapping(uint256 => mapping(address => uint256)) public donations;
    mapping(uint256 => mapping(address => bool)) public hasDonated;

    event JarCreated(
        uint256 indexed jarId,
        address indexed creator,
        string title,
        uint256 targetAmount,
        uint256 deadline
    );

    event DonationReceived(
        uint256 indexed jarId,
        address indexed donor,
        uint256 amount,
        uint256 newTotal,
        uint256 timestamp
    );

    event FundsWithdrawn(uint256 indexed jarId, address indexed creator, uint256 amount, uint256 timestamp);
    event JarStatusChanged(uint256 indexed jarId, JarStatus oldStatus, JarStatus newStatus);
    event PlatformFeeUpdated(uint256 oldBps, uint256 newBps);
    event FeesCollected(address indexed collector, uint256 amount);

    error JarNotFound();
    error NotCreator();
    error NotOwner();
    error InvalidTarget();
    error InvalidDeadline();
    error InvalidDonation();
    error InvalidPlatformFee();
    error JarNotActive();
    error CannotWithdrawYet();
    error TransferFailed();

    constructor(uint256 _feeBps) {
        if (_feeBps > MAX_PLATFORM_FEE_BPS) revert InvalidPlatformFee();
        owner = msg.sender;
        platformFeeBps = _feeBps;
    }

    function createJar(
        string calldata _title,
        string calldata _description,
        uint256 _targetAmount,
        uint256 _deadline
    ) external returns (uint256 jarId) {
        if (_targetAmount < MIN_TARGET) revert InvalidTarget();
        if (_deadline < block.timestamp + MIN_DURATION) revert InvalidDeadline();
        if (_deadline > block.timestamp + MAX_DURATION) revert InvalidDeadline();

        jarId = ++totalJars;
        jars[jarId] = Jar({
            id: jarId,
            creator: msg.sender,
            title: _title,
            description: _description,
            targetAmount: _targetAmount,
            amountRaised: 0,
            deadline: _deadline,
            status: JarStatus.Active,
            donorCount: 0,
            createdAt: block.timestamp
        });

        emit JarCreated(jarId, msg.sender, _title, _targetAmount, _deadline);
    }

    function donate(uint256 jarId) external payable {
        Jar storage jar = jars[jarId];
        if (jar.id == 0) revert JarNotFound();
        if (jar.status != JarStatus.Active) revert JarNotActive();
        if (block.timestamp >= jar.deadline) revert JarNotActive();
        if (msg.value < MIN_DONATION) revert InvalidDonation();

        if (!hasDonated[jarId][msg.sender]) {
            hasDonated[jarId][msg.sender] = true;
            jar.donorCount += 1;
        }

        donations[jarId][msg.sender] += msg.value;
        jar.amountRaised += msg.value;

        if (jar.amountRaised >= jar.targetAmount) {
            JarStatus oldStatus = jar.status;
            jar.status = JarStatus.Completed;
            emit JarStatusChanged(jarId, oldStatus, JarStatus.Completed);
        }

        emit DonationReceived(jarId, msg.sender, msg.value, jar.amountRaised, block.timestamp);
    }

    function withdraw(uint256 jarId) external {
        Jar storage jar = jars[jarId];
        if (jar.id == 0) revert JarNotFound();
        if (jar.creator != msg.sender) revert NotCreator();
        if (!canWithdraw(jarId)) revert CannotWithdrawYet();

        uint256 amount = jar.amountRaised;
        uint256 fee = (amount * platformFeeBps) / 10_000;
        uint256 creatorAmount = amount - fee;

        jar.amountRaised = 0;
        JarStatus oldStatus = jar.status;
        jar.status = JarStatus.Withdrawn;
        accumulatedFees += fee;

        (bool success, ) = payable(msg.sender).call{value: creatorAmount}("");
        if (!success) revert TransferFailed();

        emit JarStatusChanged(jarId, oldStatus, JarStatus.Withdrawn);
        emit FundsWithdrawn(jarId, msg.sender, creatorAmount, block.timestamp);
    }

    function getJar(uint256 jarId) external view returns (Jar memory) {
        if (jars[jarId].id == 0) revert JarNotFound();
        return jars[jarId];
    }

    function canWithdraw(uint256 jarId) public view returns (bool) {
        Jar memory jar = jars[jarId];
        if (jar.id == 0) return false;
        if (jar.status == JarStatus.Withdrawn) return false;
        if (jar.amountRaised == 0) return false;
        return jar.amountRaised >= jar.targetAmount || block.timestamp >= jar.deadline;
    }

    function contractBalance() external view returns (uint256) {
        return address(this).balance;
    }

    function getAllJarIds() external view returns (uint256[] memory) {
        uint256[] memory ids = new uint256[](totalJars);
        for (uint256 i = 0; i < totalJars; i++) {
            ids[i] = i + 1;
        }
        return ids;
    }

    function getProgressBps(uint256 jarId) external view returns (uint256) {
        Jar memory jar = jars[jarId];
        if (jar.id == 0) revert JarNotFound();
        if (jar.targetAmount == 0) return 0;
        return (jar.amountRaised * 10_000) / jar.targetAmount;
    }

    function getDonorAmount(uint256 jarId, address donor) external view returns (uint256) {
        if (jars[jarId].id == 0) revert JarNotFound();
        return donations[jarId][donor];
    }

    function setPlatformFee(uint256 _newFeeBps) external {
        if (msg.sender != owner) revert NotOwner();
        if (_newFeeBps > MAX_PLATFORM_FEE_BPS) revert InvalidPlatformFee();

        uint256 oldBps = platformFeeBps;
        platformFeeBps = _newFeeBps;
        emit PlatformFeeUpdated(oldBps, _newFeeBps);
    }

    function collectFees() external {
        if (msg.sender != owner) revert NotOwner();

        uint256 amount = accumulatedFees;
        accumulatedFees = 0;

        (bool success, ) = payable(msg.sender).call{value: amount}("");
        if (!success) revert TransferFailed();

        emit FeesCollected(msg.sender, amount);
    }

    function transferOwnership(address _newOwner) external {
        if (msg.sender != owner) revert NotOwner();
        if (_newOwner == address(0)) revert TransferFailed();
        owner = _newOwner;
    }

    receive() external payable {}

    fallback() external payable {}
}
