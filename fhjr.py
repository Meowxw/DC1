# 导入系统接口函数
from api.ApiTool import *
# 导入系统自带的量化分析函数
from api.QuantAPI import *

# 定义回测使用的全局变量，如果用户未定义，则使用系统默认参数
account = 100e6  # 回测初始资金
benchmark = '000300.HSZS'  # 参考业绩基准
begin_date = '2017-04-01'  # 回测起始时间
stop_date = '2018-04-16'  # 回测结束时间
fields = ['open', 'close', 'float_mv', 'pe_ttm']  # 策略中需要使用的股票因子字段

# 如果用户希望自定义印花税交易手续费等内容请定义，否则为系统默认值
order_cost = {'bid_tax': 0,  # 买入时印花税
              'ask_tax': 0.001,  # 卖出时印花税
              'bid_commission': 0.0003,  # 买入佣金
              'ask_commission': 0.0003,  # 卖出佣金
              'min_commission': 5,  # 最低佣金，元
              'slippage': 0.001,  # 滑点
              'type': 'stock',  # 股票分类
              'bid_limit': 100  # 买入最小份额限制
              }


# 初始化函数，用户在执行回测之前进行初始化工作，比如自定义参数的初始化
def init(ua=None):
    """
    该脚本的初始化程序
    :return:
    """
    # 获得股票池
    ua.param.stock_pool = getIndexComponents(index_code='000016.HSZS', tdate=begin_date)
    pass


# 用户自定义的函数
def LowPeHighGowth(ua=None, tdate=None):
    '''
    多因子选股模型：小市值、低PE、高成长
    :param ua:
    :param tdate:
    :return:
    '''
    if tdate == None:
        tdate = datetime.date.today().strftime('%Y%m%d')
    if not isTradeDate(tdate):
        print(tdate + '不是交易日！')
        return None

    # 定义低估值高成长股为 流通总市值< 100亿，市盈率 0~25，净利润增长率 > 30%
    # 读取行情数据，获取流通总市值、市盈率
    stock_data = getMarketData_T(sec_code=ua.param.stock_pool, fields=fields, tdate=tdate, right_type=-1)
    tmp_index = (stock_data['float_mv'] < 100e8) & (stock_data['pe_ttm'] > 0) & (stock_data['pe_ttm'] < 20)
    stock_selected = list(stock_data[tmp_index].index)
    # 读取财报数据，获取净利润增长率
    stock_finance_data = getFinanceData_T(sec_code=stock_selected, fields=['yoynetprofit'], tdate=tdate,
                                          has_announced=1)
    tmp_index = (stock_finance_data['yoynetprofit'] > 30)
    stock_selected = list(stock_finance_data[tmp_index].index)

    return stock_selected


# 信号生成函数，如果用户需要查看该策略每日信号，请使用该函数
def signal_generator(user_account=None, tdate=None):
    '''
    信号生成函数
    :param user_account:  用户账户
    :param tdate:         日期
    :return: 股票信号，DataFrame 格式，index 为股票代码，column=['signal'], 买入：1，卖出：-1
    '''
    stock_selected = LowPeHighGowth(ua=user_account, tdate=tdate)
    stock_signal = pd.DataFrame([], index=user_account.param.stock_pool, columns=['signal'])
    stock_signal['signal'] = [int(each_stock in stock_selected) for each_stock in stock_signal.index]
    return stock_signal


# 策略函数，用户在该函数中输入每日执行的操作，系统读取该函数进行回测
def handle_one_day(ua=None):
    '''
    策略函数
    :param ua: 用户账户，类型为系统定义的 UserAccount 类
    :return: 无
    '''
    eachdate = ua.date
    print(eachdate)
    # print(stock_pool)
    if isFirstTradeDayOfMonth(ua.date):
        # 选择股票
        stock_selected = LowPeHighGowth(ua=ua, tdate=eachdate)
        print(eachdate + '当日入选股票：')
        print(stock_selected)
        # 先以开盘价卖出全部股票
        hold_stocks = ua.position_codes
        if len(hold_stocks) > 0:
            hold_stocks_shares = [-tmp for tmp in ua.stocks_hold['shares']]
            ua.order(sec_code=hold_stocks, count=hold_stocks_shares, unit='share', price_type='open')

        # 再以收盘价买入入选股票
        if len(stock_selected) > 0:
            money_assign = [ua.cash * 0.99 / len(stock_selected)] * len(stock_selected)
            ua.order(sec_code=stock_selected, count=money_assign, unit='CNY', price_type='close')
    return
