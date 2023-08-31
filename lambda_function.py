import json
from pinnacle_client import PinnacleClient

def handler(event, context):
    params = json.loads(event["body"])

    try:
        username = params["username"]
        password = params["password"]
        home = params["home"]
        away = params["away"]
        team = params["team"]
        stake = params["stake"]
    except KeyError as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Missing required parameter: %s" % e.args[0]})
        }

    client = PinnacleClient(username, password)

    try:
        response = client.execute(home, away, team, stake)
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": str(e)})
        }

    return {
        "statusCode": 200,
        "body": response
    }
