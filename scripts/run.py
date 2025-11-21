from public.trading_bot import TradingBot

def main():
    """Initialize and run the trading bot"""
    
    print("🚀 Initializing Trading Bot...")
    
    # Create bot instance
    bot = TradingBot(
        thresholds={
            "decision_threshold": 0.7,
        },      # Use default thresholds
        buy_quantity=200,     # $100 per trade
        paper=True            # Paper trading mode
    )
    
    print("✅ Bot initialized")
    print("🔄 Starting main loop...\n")
    
    # Run main loop (this will run continuously with sleep)
    try:
        while True:
            bot.main_loop()
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Bot crashed: {e}")
        raise


if __name__ == "__main__":
    main()