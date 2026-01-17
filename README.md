# Hyperliquid Trading Challenge

## For MB and AF:
* Please refer to `helpful_but_probs_will_delete/instructions_for_dev` for specific instructions when building out APIs

## To run:
Run the following code in your root folder:

`docker compose watch`

## Limitations:
* The public API does not currently show which builder made the trade, so we treat all trades as potentially matching the target builder

## Environment Variables
Create a `.env` file and copy into it the code below

```
TARGET_BUILDER=0x010461C14e146ac35Fe42271BDC1134EE31C703a
```