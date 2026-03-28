# pynosqlc-cosmosdb

Azure Cosmos DB driver for [pynosqlc](https://github.com/alt-python/pynosqlc) — connects to Azure Cosmos DB (or the local emulator) via the azure-cosmos async client.

## Install

```
pip install alt-python-pynosqlc-cosmosdb
```

## Requirements

- Python 3.12+
- azure-cosmos 4.7+
- An Azure Cosmos DB account or the [Cosmos DB emulator](https://docs.microsoft.com/azure/cosmos-db/local-emulator)

## Usage

### Azure (production)

Pass the account endpoint in the URL and the account key in the properties dict:

```python
import asyncio
from pynosqlc.core import DriverManager, Filter
import pynosqlc.cosmosdb  # auto-registers CosmosDriver

async def main():
    async with await DriverManager.get_client(
        'pynosqlc:cosmosdb:https://myaccount.documents.azure.com:443/',
        properties={'key': '<your-account-key>', 'db_id': 'mydb'},
    ) as client:
        col = client.get_collection('orders')
        await col.store('o1', {'item': 'widget', 'qty': 5})
        f = Filter.where('qty').gt(0).build()
        async for doc in await col.find(f):
            print(doc)

asyncio.run(main())
```

### Cosmos DB Emulator (local)

Use `local` as the target — the driver connects to `http://localhost:8081` with
the well-known emulator master key automatically:

```python
async with await DriverManager.get_client(
    'pynosqlc:cosmosdb:local',
    properties={'db_id': 'mydb'},
) as client:
    ...
```

## URL scheme

```
pynosqlc:cosmosdb:<endpoint-or-local>
```

| Target | Resolves to |
|---|---|
| `local` or `localhost` | `http://localhost:8081` with emulator master key |
| `localhost:PORT` | `http://localhost:PORT` with emulator master key |
| `https://...` | Azure Cosmos DB account endpoint (requires `key` property) |

Optional properties:

| Key | Description |
|---|---|
| `key` | Account key (required for `https://` targets; omitted for emulator) |
| `db_id` | Database name (default: `'pynosqlc'`) |
| `endpoint` | Override endpoint URL (for `local`/`localhost` targets) |
