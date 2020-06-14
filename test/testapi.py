import requests
import json


def test_interaction():
    """Test interaction between api and request by asking to sum arguments."""
    url = 'http://0.0.0.0:5000/api/sum/'
    data = [[14.34, 1.68, 2.7, 25.0, 98.0, 2.8, 1.31, 0.53, 2.7, 13.0, 0.57, 1.96, 660.0]]
    j_data = json.dumps(data)
    headers = {'content-type': 'application/json', 'Accept-Charset': 'UTF-8'}
    r = requests.post(url, data=j_data, headers=headers)
    print(r, r.text)

if __name__ == "__main__":
    test_interaction()