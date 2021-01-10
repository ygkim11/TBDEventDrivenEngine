import numpy as np
import pandas as pd

def create_sharpe_ratio(returns, periods="minutely"):
    """
    Create sharpe ration for the strategy, based on a benchmark of zero
    :param returns: A pandas series representing period percentage returns.
    :param periods: Daily - 252, Hourly - 252*6.5, Minutely -252*6.5*60(한국시장은 3시 20분부터 동시호가로 갯수로는 382개 모임)
    """
    n = None
    if periods == "daily":
        n = 252
    elif periods == "hourly":
        n = 252*6.5
    elif periods == "minutely":
        n = 252*6.5*60
    else:
        print("put correct periods for sharpe ratio")

    return np.sqrt(n) * (np.mean(returns) / np.std(returns))

def create_drawdowns(pnl):
    """
    Calculatae the largest peak-to-trough drawdown of the PnL curve
    as well as the duration of the drawdown. Requires that the pnl_returns is a pandas series.
    :param pnl: A pandas series representing period percentage returns.
    :return: drawdown, duration
    """

    #Calculate the culmulative return curve
    #and set up the high water mark
    hwm = [0]
    #Code missing? 위 함수의 return series랑 뭐가 다름?

    #Create the drawdown and duration series
    idx = pnl.index
    drawdown = pd.Series(index=idx)
    duration = pd.Series(index=idx)

    #Loop over the index range
    for t in range(1, len(idx)):
        hwm.append(max(hwm[t-1], pnl[t]))
        drawdown[t] = hwm[t] - pnl[t] #이거 맞나? 나누기 pnl[t] 해줘야될듯
        duration[t] = (0 if drawdown[t] == 0 else duration[t-1]+1)
    return drawdown, drawdown.max(), duration.max()