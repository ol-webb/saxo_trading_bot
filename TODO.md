

# TO DO

## Near Future

1. fetch ticker price info before placing order, so we base the quantity on the value of the stock price, not just the number of shares



## Further Future

### Robustness

1. unlikely, but we could have multiple outstanding orders for an asset, currently when iterating through "orders" we just pick the first one that matches the ticker. We might have multiple.