import yfinance as yf
import requests
import os
from datetime import datetime

# 監視対象の企業グループを定義
COMPANY_GROUPS = {
    "ビットコイン保有企業": ["MSTR", "SMLR", "NAKA", "PRE", "GME"],
    "Hyperliquid保有企業": ["HYPD"],
    "イーサリアム保有企業": ["BTBT", "SBET", "BMNR"],
    "クリプト事業": ["GLXY.TO", "BKKT", "HOOD", "CRCL.L", "COIN"]
}

# DiscordのWebhook URLを環境変数から取得
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

def get_stock_data():
    """Yahoo Financeから株価データを取得・整形する"""
    all_tickers = [ticker for tickers in COMPANY_GROUPS.values() for ticker in tickers]
    
    # 過去3営業日分のデータを一括取得
    data = yf.download(all_tickers, period="3d", progress=False, no_cache=True)
    
    if len(data['Close']) < 2:
        raise ValueError("2日分の取引データが取得できませんでした。市場が休場だった可能性があります。")
        
    return data['Close']

def format_message(stock_data):
    """Discordに送信するためのメッセージ（Embed）を作成する"""
    
    # 前営業日の日付
    last_trading_day = stock_data.index[-1].strftime('%Y-%m-%d')
    
    # Discord Embedsの基本構造
    embed = {
        "title": f"📈 定期株価レポート ({last_trading_day})",
        "description": "主要クリプト関連企業の株価（前日終値）です。",
        "color": 3447003,  # 青系の色
        "fields": []
    }

    # グループごとに株価情報をフィールドとして追加
    for group_name, tickers in COMPANY_GROUPS.items():
        field_value = ""
        for ticker in tickers:
            try:
                prev_close = stock_data[ticker].iloc[-1]
                day_before_close = stock_data[ticker].iloc[-2]
                change_pct = ((prev_close - day_before_close) / day_before_close) * 100
                
                # サフィックス (.TO, .L) を除いたティッカー名
                display_ticker = ticker.split('.')[0]
                
                # 符号付きでパーセンテージを整形
                change_str = f"{change_pct:+.2f}%"
                
                field_value += f"`{display_ticker:<5}`: **${prev_close:8.2f}** ({change_str})\n"
            except (KeyError, IndexError):
                field_value += f"`{ticker:<5}`: データ取得エラー\n"
        
        embed["fields"].append({
            "name": f"▼ {group_name}",
            "value": field_value,
            "inline": False
        })
        
    return embed

def send_to_discord(embed):
    """整形したメッセージをDiscordに送信する"""
    if not DISCORD_WEBHOOK_URL:
        print("エラー: 環境変数 DISCORD_WEBHOOK_URL が設定されていません。")
        return

    payload = {"embeds": [embed]}
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()  # エラーがあれば例外を発生させる
        print("Discordへの通知に成功しました。")
    except requests.exceptions.RequestException as e:
        print(f"Discordへの通知中にエラーが発生しました: {e}")

def main():
    """メイン処理"""
    try:
        print("株価データを取得しています...")
        stock_data = get_stock_data()
        print("メッセージを整形しています...")
        message_embed = format_message(stock_data)
        print("Discordに通知を送信しています...")
        send_to_discord(message_embed)
    except Exception as e:
        # 実行中にエラーが発生した場合もDiscordに通知する
        error_embed = {
            "title": "❌ 株価取得スクリプト実行エラー",
            "description": f"処理中にエラーが発生しました。\n```\n{e}\n```",
            "color": 15158332 # 赤色
        }
        send_to_discord(error_embed)

if __name__ == "__main__":
    main()
