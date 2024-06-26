from flask import Flask, jsonify, request
from blockchain import Blockchain
import dataclasses
import requests
import argparse
# python3 ./node.py -i Node5000 -p 5000

app = Flask(__name__)


@app.route("/chain", methods=["GET", "POST"])
def chain():
    if request.method == "GET":
        response = {
            "chain": [dataclasses.asdict(block) for block in local_blockchain.chain],
            "length": len(local_blockchain.chain),
        }
        return jsonify(response), 200
    else:
        new_chain = request.get_json()
        replaced = local_blockchain.receive_chain(new_chain)
        if replaced:
            response = {
                "message": "The chain was replaced",
                "chain": local_blockchain.chain,
            }
        else:
            response = {
                "message": "No changes to the chain",
                "chain": local_blockchain.chain,
            }

        return jsonify(response), 200


@app.route("/mine", methods=["GET"])
def mine():
    local_blockchain.mine()

    response = {
        "status": "Success",
        "index": local_blockchain.current_block().index,
        "transactions": [
            dataclasses.asdict(t) for t in local_blockchain.current_block().transactions
        ],
        "proof": local_blockchain.current_block().proof,
    }

    return jsonify(response), 200


@app.route("/transactions/new", methods=["POST"])
def new_transaction():
    values = request.get_json()
    required = ["sender", "recipient", "amount"]
    
    # validate transaction by signature
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    m = values["sender"] + " sends "+ values["recipient"] +" "+ str(values["amount"])+" dollars"
    message = m.encode('utf-8')
    # message = b"Gary sends Eric 10 dollars"  # Make sure to encode the message as bytes
    signature = private_key.sign(message, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
    print(type(signature))
    public_key = private_key.public_key()
    if not public_key.verify(signature,message,padding.PSS(mgf=padding.MGF1(hashes.SHA256()),salt_length=padding.PSS.MAX_LENGTH),hashes.SHA256()):
        exit(1)


    
    if not values or not all(k in values for k in required):
        return "Missing values", 400

    local_blockchain.add_transaction(
        values["sender"], values["recipient"], values["amount"]
    )

    response = {
        "message": f"Transaction will be added to block {local_blockchain.next_index()}"
    }
    return jsonify(response), 201


@app.route("/network", methods=["GET", "POST"])
def network():
    if request.method == "GET":
        response = {"nodes": list(local_blockchain.players)}
        return jsonify(response), 200
    else:
        value = request.get_json()
        if not value or not ("address" in value):
            return "Missing values", 400

        local_blockchain.add_player(value["address"])

        response = {"message": f"Added player address {value['address']}"}
        return jsonify(response), 200


@app.route("/broadcast", methods=["GET"])
def broadcast():
    successful_broadcasts = []
    for a in local_blockchain.players:
        try:
            r = requests.post(
                a + "/chain",
                json=[dataclasses.asdict(block) for block in local_blockchain.chain],
            )
            successful_broadcasts.append(a)
        except Exception as e:
            print("Failed to send to ", a)
            print(e)
    response = {"message": "Chain broadcasted", "recipients": successful_broadcasts}
    return jsonify(response), 200


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a node in a blockchain network.")
    parser.add_argument("-i", "--identifier", default="")
    parser.add_argument("-p", "--port", default="5000")

    args = parser.parse_args()
    identifier = args.identifier
    port_num = args.port
    difficulty_number = 2
    mining_reward = 10
    local_blockchain = Blockchain(identifier, difficulty_number, mining_reward)

    app.run(port=port_num)