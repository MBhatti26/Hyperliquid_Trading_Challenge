# Hyperliquid Trading Challenge

## How to run:
Run the following code in your root folder:

`docker compose watch`

## Implementation
The following endpoints are accessible via this API:
* GET: `/v1/trades?user=&coin=&fromMs=&toMs=&builderOnly=false`
* GET: `v1/positions/history?user=&coin&fromMs=&toMs=&builderOnly=false`
* GET: `v1/pnl?user=&coin=&fromMs=&toMs=&builderOnly=false`
* GET: `v1/leaderbaord?coin=&fromMs=&toMs=&metric=volume|pnl|returnPct&builderOnly=true&maxStartCapital=1000`

## Environment Variables
We used the following environment variables:
* Builder address: `0x010461C14e146ac35Fe42271BDC1134EE31C703a`
* Wallet address: `0x010461C14e146ac35Fe42271BDC1134EE31C703a`

**To access builder address**
Create a `.env` file and copy into it the code below

```
TARGET_BUILDER=0x010461C14e146ac35Fe42271BDC1134EE31C703a
```

## Limitations:
* The public API does not currently show which builder made the trade, so we treat all trades as potentially matching the target builder
* Since the public API does not explicitly label builder addresses, we identify builder trades by checking if a builder fee was present
