from hashlib import sha256
import json, time


class Block:
    def __init__(self, index, transactions, timestamp, prev_hash, nonce=0):
        # 索引
        self.index = index
        # 事务
        self.transactions = transactions
        # 时间戳
        self.timestamp = timestamp
        # 前区块的hash值
        self.prev_hash = prev_hash
        # 计算次数
        self.nonce = nonce

    def compute_hash(self):
        # 计算当前区块的hash值
        block_str = json.dumps(self.__dict__, sort_keys=True)
        return sha256(block_str.encode()).hexdigest()


class Blockchain:
    # 工作算法难度
    difficulty = 2

    def __init__(self):
        # 保存未提交的事务
        self.transactions = []
        # 区块链
        self.chain = []

    def create_genesis_block(self):
        # 创世区块
        genesis_block = Block(0, [], time.time(), "0")
        # 挂载hash值
        genesis_block.hash = genesis_block.compute_hash()
        # 加入区块链中
        self.chain.append(genesis_block)

    # 返回最后一块区块
    # @property类似使用属性
    @property
    def last_block(self):
        return self.chain[-1]

    # 工作证明算法
    def proof_of_work(self, block):
        # 初次计算的hash值
        computed_hash = block.compute_hash()
        # 循环计算hash值 直到满足要求
        # block的hash值要求：hash满足以两个0开头
        while not computed_hash.startswith("0" * Blockchain.difficulty):
            block.nonce += 1
            computed_hash = block.compute_hash()

        # 返回满足要求的hash值
        return computed_hash

    # 添加区块
    def add_block(self, block, proof):
        # 验证区块链的最后一个区块的hash值是否和当前区块的前区块hash值相同
        prev_hash = self.last_block.hash
        if prev_hash != block.prev_hash:
            return False

        # 验证计算出来的区块hash值是否和传入的hash值相同
        if not Blockchain.is_valid_proof(block, proof):
            return False

        # 挂载hash到区块上
        block.hash = proof
        # 添加区块到区块链
        self.chain.append(block)
        return True

    @classmethod
    # 验证传入的hash和区块hash是否匹配并满足条件
    def is_valid_proof(cls, block, block_hash):
        return (
            block_hash.startswith("0" * Blockchain.difficulty)
            and block_hash == block.compute_hash()
        )

    @classmethod
    # 验证区块链是否合法
    def check_chain_validity(cls, chain):
        # 默认区块链是有效的
        result = True
        # 创世区块的prev_hash为"0"
        prev_hash = "0"

        # 依次验证区块的hash值
        for block in chain:
            block_hash = block.hash
            # 删除dict上的元素
            delattr(block, "hash")

            # 如果计算的hash值和hash值不同或者prev_hash值和前区块的hash值不同，
            # 则区块链为无效，同时结束验证
            if (
                not cls.is_valid_proof(block, block_hash)
                or prev_hash != block.prev_hash
            ):
                result = False
                break

            block.hash, prev_hash = block_hash, block_hash

        return result

    # 添加新的事务
    def add_new_transaction(self, transaction):
        self.transactions.append(transaction)

    # 挖坑
    def mine(self):
        # 没有事务则直接返回
        if not self.transactions:
            return False

        last_block = self.last_block

        # 创建新的区块
        new_block = Block(
            index=last_block.index + 1,
            transactions=self.transactions,
            timestamp=time.time(),
            prev_hash=last_block.hash,
        )

        # 计算新的区块的hash
        proof = self.proof_of_work(new_block)
        # 添加新的区块
        self.add_block(new_block, proof)
        # 将当前的事务列表清空
        self.transactions = []
        # 创建成功返回新的区块的index值
        return new_block
