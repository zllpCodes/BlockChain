from flask import Flask, request
import requests, time, json, sys
from blockChain import Blockchain, Block

# 创建本地服务
app = Flask(__name__)
# 创建区块链
blockchain = Blockchain()
# 创建创世区块
blockchain.create_genesis_block()
# 对等网点
peers = set()
localPeer = ""


# 添加事务
@app.route("/new_transaction", methods=["POST"])
def new_transaction():
    tx_data = request.get_json()
    required_fields = ["author", "content"]

    # 验证参数是否缺失
    for field in required_fields:
        if not tx_data or not tx_data.get(field):
            return "Invalid transaction data", 400

    tx_data["timestamp"] = time.time()
    blockchain.add_new_transaction(tx_data)

    return "Success", 200


# 现有事务列表
@app.route("/get_transactions", methods=["GET"])
def get_transactions():
    return json.dumps(blockchain.transactions)


# 返回区块链列表
@app.route("/chain", methods=["GET"])
def get_chain():
    return chain_str()


# 返回区块链列表
def chain_str():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)

    print(f"chain_data:{chain_data}")
    return json.dumps(
        {"length": len(chain_data), "chain": chain_data, "peers": list(peers)}
    )


# 挖矿
@app.route("/mine", methods=["GET"])
def mine_transactions():
    global blockchain

    result = blockchain.mine()
    if result:
        # 广播新挖到的区块
        announce_new_block(result)
        return f"Block #{result.index} is mined.", 200
    else:
        return "No transactions to mine.", 404


# 添加网点
@app.route("/register_node", methods=["POST"])
def register_new_peers():
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400

    peers.add(node_address)
    return get_chain()


# 以某个存在的结点为模板注册网点
@app.route("/register_with", methods=["POST"])
def register_with_existing_peers():
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400

    data = {"node_address": request.host_url}
    headers = {"Content-Type": "application/json"}
    response = requests.post(
        f"{node_address}register_node", data=json.dumps(data), headers=headers
    )

    if response.status_code == 200:
        global blockchain
        global peers
        chain_dump = response.json()["chain"]
        blockchain = create_chain_from_dump(chain_dump)
        peers.update(response.json()["peers"])
        return "Registrations successful", 200
    else:
        return response.content, response.status_code


def create_chain_from_dump(chain_dump):
    blockchain = Blockchain()
    for idx, block_data in enumerate(chain_dump):
        block = Block(
            block_data["index"],
            block_data["transactions"],
            block_data["timestamp"],
            block_data["prev_hash"],
            block_data["nonce"],
        )
        if idx > 0:
            proof = block_data["hash"]
            added = blockchain.add_block(block, proof)
            if not added:
                raise Exception("The chain dump is tampered!!")
        else:
            # 添加创世区块
            block.hash = block_data["hash"]
            blockchain.chain.append(block)

    return blockchain


# 将网络中新挖到的区块添加到本地区块链中
@app.route("/add_block", methods=["POST"])
def verify_and_add_block():
    block_data = request.get_json()
    print(f"block_data:{block_data}")
    block = Block(
        block_data["index"],
        block_data["transactions"],
        block_data["timestamp"],
        block_data["prev_hash"],
        block_data["nonce"]
    )

    proof = block_data["hash"]
    added = blockchain.add_block(block, proof)

    if not added:
        return "The block was discarded by the node", 400

    return "Block added to the chain", 200


# 寻找最长有效区块链并更新
@app.route("/max_chain", methods=["GET"])
def consensus():
    # 使用全局变量blockchain
    global blockchain
    global peers

    longest_chain = None
    current_len = len(blockchain.chain)

    # 在注册网点中，寻找最长有效链
    for peer in peers:
        if peer is not localPeer:
            print(f"consensus peer:{peer}")
            response = requests.get(f"{peer}chain")
            try:
                response = response.json()
                print(f"response:{response}")
                length = response["length"]
                chain = response["chain"]
                chain = create_chain_from_dump(chain)
                # 若此网点中的区块链比当前的长且是有效的区块链，
                # 则修改当前最长区块链和最大长度
                if length > current_len and blockchain.check_chain_validity(chain):
                    current_len = length
                    longest_chain = chain
            except json.decoder.JSONDecodeError:
                print(f"error response:{response}")

    # 如果找到更长的区块链，则将当前的区块链与之等同
    if longest_chain:
        print(f"longest_chain:{longest_chain}")
        blockchain = create_chain_from_dump(longest_chain)

    return chain_str()


# 发布挖到新区块的消息
def announce_new_block(block):
    global peers

    for peer in peers:
        if peer is not localPeer:
            print(f"announce block:{block.__dict__}")
            url = f"{peer}add_block"
            requests.post(
                url,
                data=json.dumps(block.__dict__, sort_keys=True),
                headers={"Content-Type": "application/json"},
            )


if __name__ == "__main__":
    host = "127.0.0.1"
    port = sys.argv[1]
    # 注册本地网点
    localPeer = f"http://{host}:{port}/"
    peers.add(localPeer)
    print(f"peers:{json.dumps(list(peers))}")
    # 运行本地服务
    app.run(debug=True, host=host, port=int(port))

