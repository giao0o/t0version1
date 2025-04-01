import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class TradingSystem:
    def __init__(self):
        self.position = 0  # 持仓状态 0:空仓 1:持多
        self.last_trade_price = None  # 上次交易价格
        self.trade_log = []  # 交易记录

    def get_trade_data(self, stock_code, index_code, days=60):
        now = datetime.now()
        end_date = now.strftime("%Y%m%d")
        start_date = (now - timedelta(days=days*2)).strftime("%Y%m%d")
        
        # 获取前复权数据
        stock_df = ak.stock_zh_a_daily(
            symbol=stock_code, 
            start_date=start_date, 
            end_date=end_date, 
            adjust="qfq"
        )
        
        # 获取大盘数据
        index_df = ak.stock_zh_index_daily(symbol=index_code).rename(columns={
            'date': 'date',
            'close': 'index_close'
        })
        
        # 统一处理日期索引
        stock_df['date'] = pd.to_datetime(stock_df['date'])
        stock_df = stock_df.set_index('date').sort_index()
        
        index_df['date'] = pd.to_datetime(index_df['date'])
        index_df = index_df.set_index('date').sort_index()
        
        return stock_df, index_df

    def calculate_indicators(self, df):
        # 增强指标计算
        df['MA5'] = df['close'].rolling(5).mean()
        df['MA20'] = df['close'].rolling(20).mean()
        df['MA60'] = df['close'].rolling(60).mean()
        
        # 动态波动率计算
        df['ATR'] = df['high'].rolling(14).max() - df['low'].rolling(14).min()
        
        # 增强RSI计算
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        df['RSI'] = 100 - (100 / (1 + (gain.ewm(alpha=1/14).mean() / 
                                     loss.ewm(alpha=1/14).mean())))
        
        # 动态支撑阻力
        df['Pivot'] = (df['high'] + df['low'] + df['close']) / 3
        df['S1'] = 2*df['Pivot'] - df['high']
        df['R1'] = 2*df['Pivot'] - df['low']
        
        return df

    def generate_daily_signal(self, stock_data, index_data):
        latest = stock_data.iloc[-1]
        prev = stock_data.iloc[-2] if len(stock_data) > 1 else latest
        
        # 趋势判断
        trend_up = latest['MA5'] > latest['MA20'] > latest['MA60']
        trend_down = latest['MA5'] < latest['MA20'] < latest['MA60']
        
        # 波动率调整
        atr_factor = latest['ATR'] / latest['close']
        
        # 强制交易逻辑
        if self.position == 0:  # 空仓状态
            if trend_up and latest['RSI'] < 70:
                entry_price = min(latest['close']*0.995, latest['S1'])
                stop_loss = entry_price - 2*latest['ATR']
                return {
                    'action': 'buy',
                    'price': round(entry_price, 2),
                    'stop_loss': round(stop_loss, 2),
                    'target': round(entry_price + 3*latest['ATR'], 2)
                }
            else:  # 趋势跟踪策略
                return {
                    'action': 'buy' if trend_up else 'sell',
                    'price': latest['close'],
                    'stop_loss': latest['close']*0.98,
                    'target': latest['close']*1.03
                }
                
        else:  # 持多状态
            current_return = (latest['close'] - self.last_trade_price) / self.last_trade_price
            if current_return > 0.03 or latest['RSI'] > 70:
                return {
                    'action': 'sell',
                    'price': latest['close']*1.005,
                    'reason': '止盈/超买'
                }
            elif current_return < -0.02:
                return {
                    'action': 'sell',
                    'price': latest['close']*0.995,
                    'reason': '止损'
                }
            else:
                return {
                    'action': 'hold',
                    'price': latest['close'],
                    'reason': '持仓观望'
                }

    def execute_trade(self, signal):
        # 记录交易
        trade = {
            'datetime': datetime.now(),
            'action': signal['action'],
            'price': signal.get('price'),
            'position': self.position
        }
        self.trade_log.append(trade)
        
        # 更新持仓状态
        if signal['action'] == 'buy':
            self.position = 1
            self.last_trade_price = signal['price']
        elif signal['action'] == 'sell':
            self.position = 0
            self.last_trade_price = None

    def run_daily_strategy(self, stock_code='sz300935', index_code='sh000001'):
        try:
            # 获取数据
            stock_df, index_df = self.get_trade_data(stock_code, index_code)
            
            # 计算指标
            stock_df = self.calculate_indicators(stock_df)
            index_df['index_ma20'] = index_df['index_close'].rolling(20).mean()
            
            # 生成信号
            signal = self.generate_daily_signal(stock_df, index_df)
            self.execute_trade(signal)
            
            # 输出结果
            print("="*40)
            print(f"交易日: {stock_df.index[-1].strftime('%Y-%m-%d')}")
            print(f"最新收盘价: {stock_df['close'].iloc[-1]}")
            print(f"操作指令: {signal['action'].upper()}")
            print(f"执行价格: {signal.get('price', 'N/A')}")
            if 'stop_loss' in signal:
                print(f"止损价位: {signal['stop_loss']}")
            if 'target' in signal:
                print(f"目标价位: {signal['target']}")
            print(f"逻辑说明: {signal['reason']}")
            print("="*40)
            
        except Exception as e:
            print(f"策略执行异常: {str(e)}")

if __name__ == "__main__":
    trader = TradingSystem()
    trader.run_daily_strategy()