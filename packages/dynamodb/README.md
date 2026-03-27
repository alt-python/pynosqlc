# pynosqlc-dynamodb

DynamoDB driver for [pynosqlc](https://github.com/alt-python/pynosqlc) — connects to Amazon DynamoDB (or DynamoDB Local) via aioboto3.

## Install

```
pip install pynosqlc-dynamodb
```

## Requirements

- Python 3.12+
- aioboto3 2.7+
- AWS credentials configured (`~/.aws/credentials`, environment variables, or IAM role)
- For local development: [DynamoDB Local](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html)

## Usage

### AWS (production)

```python
import asyncio
from pynosqlc.core import DriverManager, Filter
import pynosqlc.dynamodb  # auto-registers DynamoDriver

async def main():
    async with DriverManager.get_client('pynosqlc:dynamodb:us-east-1') as client:
        col = client.collection('orders')
        await col.store('o1', {'item': 'widget', 'qty': 5})
        f = Filter.where('qty').gt(0)
        async for doc in await col.find(f):
            print(doc)

asyncio.run(main())
```

### DynamoDB Local

Pass `endpoint` in the properties dict to point at a local instance:

```python
async with DriverManager.get_client(
    'pynosqlc:dynamodb:us-east-1',
    properties={'endpoint': 'http://localhost:8000'},
) as client:
    ...
```

## URL scheme

```
pynosqlc:dynamodb:<aws-region>
```

Example: `pynosqlc:dynamodb:us-east-1`

Optional properties:

| Key | Description |
|---|---|
| `endpoint` | Override endpoint URL (e.g. `http://localhost:8000` for DynamoDB Local) |
| `aws_access_key_id` | AWS access key (falls back to environment / credential chain) |
| `aws_secret_access_key` | AWS secret key (falls back to environment / credential chain) |
