# Alpaca Trading Bot

## What Is It & How Does It Work?

Principally: a trading bot template. With a given table of assets with certain key features, this bot will trade based around signals that you can set. It uses Alpaca brokerage.

The *holdings* table, contains features *signal* and *position_state* (described in more detail later). *Signal* tells us whether to buy, sell or hold, and *position_state* (TEXT) tells us the state of an asset based on any live positions or pending orders. The bot reconciles these two features, so when we have a buy signal, the position state must fit into certain categories.  

You can insert your own logic for a signal engine to update the table with new assets and new signals. Provided with the relevant keys, the bot will update *position_state* and reconcile it with *signal* by placing or cancelling orders.

## 