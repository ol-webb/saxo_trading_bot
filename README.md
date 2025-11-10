# Alpaca Trading Bot

I previously used IBKR, however their gateway service is not designed to be run headless and requires the user to input username and password through a GUI. In July 2025, Alpaca entered UK markets, so with the future aims of running my bots headless through AWS, I am using Alpaca instead of IBKR.

## What Is It & How Does It Work?

Principally: a trading bot template. With a given table of assets with certain key features, this bot will trade based around signals that you can set. It uses Alpaca brokerage.

The *holdings* table, contains features *signal* and *position_state* (described in more detail later). *Signal* tells us whether to buy, sell or hold, and *position_state* (TEXT) tells us the state of an asset based on any live positions or pending orders. The bot reconciles these two features, so when we have a buy signal, the position state must fit into certain categories.  

You can insert your own logic for a signal engine to update the table with new assets and new signals. Provided with the relevant keys, the bot will update *position_state* and reconcile it with *signal* by placing or cancelling orders.

### Repo Layout

The system design is outlined in ARCHITECTURE.md  
The bot is entirely in trading_bot.py

## Requirements

### database
Some database (.db) containing table *holdings. Essential columns:
- *signal* TEXT
- *position_state* TEXT
- *cik_ticker* TEXT unique identifier for an asset
- *quantity_bought* REAL number of shares owned

### Signal Engine
Some external object used to refresh *holdings*. Particularly, it should refresh *signal* based on whatever algorithm you are using, and perhaps add or remove rows. Key methods:
- signalengine.run_section_one()
- signalengine.run_holdings_engine_refresh

Those could of course be combined into one method. run_section_one() can be used to run any models or background tasks. run_holdings_engine_refresh() can be used to act directly on *holdings* table.



