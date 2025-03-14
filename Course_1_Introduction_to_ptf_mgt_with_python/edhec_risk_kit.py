import pandas as pd
import scipy.stats
import numpy as np
from scipy.optimize import minimize

def drawdown(returns_series: pd.Series):
    """
    doc string -->
    Takes a time series of assets returns
    Computes and returns a dataFraùe that contains:
    the wealth index
    the previous peaks
    percentage drawdons
    """
    wealth_index = 1000*(1+returns_series).cumprod()
    previous_peaks = wealth_index.cummax()
    drawdowns = (wealth_index - previous_peaks) / previous_peaks
    
    return pd.DataFrame({
        "Wealth":wealth_index,
        "Peaks":previous_peaks,
        "Drawdown":drawdowns
    })

def get_ffme_returns():
    """éz"e
    Load the fama-french Dataset for the returns of the top and bottom deciles by MarketCap
    """
    me_m = pd.read_csv(" /Portfolios_Formed_on_ME_monthly_EW.csv", header = 0, index_col = 0,
                     parse_dates = True, na_values= -99.99)
    rets = me_m[['Lo 10', 'Hi 10']]
    rets.columns = ['SmallCap', 'LargeCap']
    rets = rets/100
    rets.index = pd.to_datetime(rets.index, format="%Y%m")
    
    return rets

def get_hfi_returns():
    """
    Load and format the EDHEC hedge fund index returns
    """
    hfi = pd.read_csv("data/edhec-hedgefundindices.csv", header = 0, index_col = 0,parse_dates = True)
    hfi = hfi/100
    hfi.index = hfi.index.to_period('M')
    
    return hfi

def get_ind_returns():
    """
    Load and format the Ken french 30 industry portfolio value weoghed monthly returns
    """
    ind = pd.read_csv("data/ind30_m_vw_rets.csv", header = 0, index_col = 0, parse_dates = True)/100
    ind.index = pd.to_datetime(ind.index, format = '%Y%m').to_period('M')
    ind.columns = ind.columns.str.strip()
    
    return ind

def get_ind_size():
    """
    Load and format the Ken french 30 industry portfolio size
    """
    ind = pd.read_csv("data/ind30_m_size.csv", header = 0, index_col = 0, parse_dates = True)
    ind.index = pd.to_datetime(ind.index, format = '%Y%m').to_period('M')
    ind.columns = ind.columns.str.strip()
    
    return ind

def get_ind_nfirms():
    """
    Load and format the Ken french 30 industry portfolio number of firms
    """
    ind = pd.read_csv("data/ind30_m_nfirms.csv", header = 0, index_col = 0, parse_dates = True)
    ind.index = pd.to_datetime(ind.index, format = '%Y%m').to_period('M')
    ind.columns = ind.columns.str.strip()
    
    return ind

def get_total_market_index_returns():
    """
    Load and format the Ken french 30 industry portfolio number of firms
    --> compute the total market index returns
    """
    ind_return = get_ind_returns()
    ind_nfirms = get_ind_nfirms()
    ind_size = get_ind_size()
    ind_mktcap = ind_nfirms * ind_size
    total_mktcap = ind_mktcap.sum(axis="columns")
    ind_capweight = ind_mktcap.divide(total_mktcap, axis = 'rows')
    total_market_return = (ind_capweight * ind_return).sum(axis="columns")
    
    return total_market_return



def skewness(r):
    """
    Alternative to scipy.stats.skew()
    Computes the skeness of the supplied series or DataFrame
    returns a float or a series
    """
    demeaned_r = r - r.mean()
    # use the population standard deviation, so set degree of freedom (ddof) to 0
    sigma_r = r.std(ddof=0)
    exp = (demeaned_r**3).mean()
    
    return exp/sigma_r**3

def kurtosis(r):
    """
    Alternative to scipy.stats.kurtosis()
    Computes the kurtosis of the supplied series or DataFrame
    returns a float or a series
    """
    demeaned_r = r - r.mean()
    # use the population standard deviation, so set degree of freedom (ddof) to 0
    sigma_r = r.std(ddof=0)
    exp = (demeaned_r**4).mean()
    
    return exp/sigma_r**4

def is_normal(r, level = 0.01):
    """
    Applies the Jarque-Bera test to determine if a series is normal or not
    Test is applied at the 1% level yb default
    Returns True if the hypothesis of normality is accepted, False otherwise
    """
    
    statistic, p_value = scipy.stats.jarque_bera(r)
    
    return p_value > level

def semideviation(r):
    """
    Returns the semideviation aka negative semideviation of r
    r must be a series or a dataframe
    """
    is_negative = r < 0
    return r[is_negative].std(ddof=0)

def semideviation_below_mean(r):
    """
    Returns the semideviation aka negative semideviation of r below the mean
    r must be a series or a dataframe
    """
    excess = r - r.mean()
    excess_negative = excess[excess<0]
    excess_negative_square = excess_negative**2
    n_negative = (excess<0).sum()
    return (excess_negative_square.sum()/n_negative)**0.5

def var_historic(r, level=5):
    """
    Returns the historic Value At Risk at a specified level
    i.e. returns the number such that 'level' percent of returns
    fall below that number, and the 100-level percent are above
    """
    if isinstance(r, pd.DataFrame):
        # if dataframe we want to apply the function to series in order to conserv the index and format
        return r.aggregate(var_historic, level=level)
    elif isinstance(r, pd.Series):
        # using the percentile function of numpy, 
        # ading neg sign as VaR are generally reported as positiv values knowing we are talking about losses
        return -np.percentile(r, level)
    else:
        raise TypeError("Expected r to be Series or DataFrame")

from scipy.stats import norm

def var_gaussian(r, level=5, modified= False):
    """
    Return the Parametric Gaussian VaR of a Series or DataFrame
    if "modified" is True, then the modified VaR is returned,
    using the Cornish-Fisher modification
    """
    # compute the 2 score assuming it gaussian
    z_score = norm.ppf(level/100)
    
    if modified:
        # modify the Z-score based on observed skewness and Kurtosis
        s = skewness(r)
        k = kurtosis(r)
        z_score = (z_score + 
                           (z_score**2-1)*s/6 +
                           (z_score**3 - 3*z_score)*(k-3)/24 -
                           (2*z_score**3 - 5*z_score)*(s**2)/36
                    )
    
    return - ( r.mean() + z_score*r.std(ddof=0) )


def cvar_historic(r,level=5):
    """
    Computes the conditionnal VaR of Series or DataFrame
    """
    if isinstance(r, pd.Series):
        is_beyond = r <= -var_historic(r,level=level)
        return -r[is_beyond].mean()
    elif isinstance(r, pd.DataFrame):
        return r.aggregate(cvar_historic, level=level)
    else:
        raise TypeError("Expected r to be Series or DataFrame")
        
def annualize_rets(r,periods_per_year):
    """
    Annualizes a set of returns
    we should infer the periods per year but that is currently left as an exercise to the reader :)
    """
    compounded_growth = (1+r).prod()
    n_periods = r.shape[0]
    return compounded_growth**(periods_per_year/n_periods) - 1

def annualize_vol(r,periods_per_year):
    """
    Annualizes the vol of a set of returns
    we should infer the periods per year but that is currently left as an exercise to the reader :)
    """
    return r.std()*(periods_per_year**0.5)

def sharpe_ratio(r, riskfree_rate,periods_per_year):
    """
    Computes the annualized sharpe ratio of a set of returns
    """
    rf_per_period = (1+riskfree_rate)**(1/periods_per_year) - 1
    excess_ret = r - rf_per_period
    ann_excess_ret = annualize_rets(excess_ret, periods_per_year)
    ann_vol = annualize_vol(r, periods_per_year)
    
    return ann_excess_ret/ann_vol


def portfolio_return(weights, returns):
    """
    weights --> return
    """
    return weights.T @ returns #matrix multiplication


def portfolio_vol(weights, covmat):
    """
    weights --> vol
    """
    return (weights.T @ covmat @ weights)**0.5

def plot_ef2(n_points, er, cov, style=".-"):
    """
    plot the 2-asset efficient frontier
    """
    if er.shape[0] != 2 or cov.shape[0] != 2:
        raise ValueError("Plot_ef2 can only plot 2-asset frontiers")
    # list comprehension structure to be prefer to normal for loop
    weights = [np.array([w,1-w]) for w in np.linspace(0,1,n_points)]
    rets = [portfolio_return(w, er) for w in weights]
    vols = [portfolio_vol(w, cov) for w in weights]
    ef = pd.DataFrame({"Returns":rets,"Volatility":vols})
    
    return ef.plot.line(x="Volatility", y="Returns", style=style)

def minimize_vol(target_return, er, cov):
    """
    target_ret --> w
    """
    n = er.shape[0]
    init_guess = np.repeat(1/n, n) # could be whatever we like but sum equals 1
    bounds = ((0.0,1.0), )*n # tuple of tuple
    return_is_target = {
        'type':'eq',
        'args': (er,),
        'fun': lambda weights, er: target_return - portfolio_return(weights, er)
    }
    weights_sum_to_1 = {
        'type':'eq',
        'fun': lambda weights: np.sum(weights) - 1
    }
    
    results = minimize(portfolio_vol, init_guess,
                       args= (cov,), method="SLSQP",
                       options={'disp': False},
                       constraints = (return_is_target, weights_sum_to_1),
                       bounds = bounds
                      )
    return results.x

def optimal_weights(n_points, er, cov):
    """
    Returns the weighs of the portfolio that gives you the maximum sharpe ratio
    given the riskfree rate and expected returns and a covariance matrix
    """
    target_rets = np.linspace(er.min(), er.max(), n_points)
    weights = [minimize_vol(target_return, er, cov) for target_return in target_rets]
    return weights

def msr(riskfree_rate, er, cov):
    """
    riskfree_rate + ER + COV --> w
    """
    n = er.shape[0]
    init_guess = np.repeat(1/n, n) # could be whatever we like but sum equals 1
    bounds = ((0.0,1.0), )*n # tuple of tuple
    weights_sum_to_1 = {
        'type':'eq',
        'fun': lambda weights: np.sum(weights) - 1
    }
    
    def neg_sharpe_ratio(weights, riskfree_rate, er, cov):
        """
        returns the negative of the sharpe ratio, given weights
        """
        r = portfolio_return(weights, er)
        vol = portfolio_vol(weights, cov)
        return -(r - riskfree_rate)/vol
    
    
    results = minimize(neg_sharpe_ratio, init_guess,
                       args= (riskfree_rate, er, cov,), method="SLSQP",
                       options={'disp': False},
                       constraints = (weights_sum_to_1),
                       bounds = bounds
                      )
    return results.x

def gmv(cov):
    """
    Returns the weight of Global Minimum Vol portfolio 
    given the covariance matrix
    """
    n = cov.shape[0]
    return msr(0,np.repeat(1,n), cov)
    
def plot_ef(n_points, er, cov, style=".-", show_cml = False, riskfree_rate=0, show_ew = False, show_gmv = False):
    """
    plot the N-asset efficient frontier
    """
    weights = optimal_weights(n_points, er, cov)
    rets = [portfolio_return(w, er) for w in weights]
    vols = [portfolio_vol(w, cov) for w in weights]
    ef = pd.DataFrame({"Returns":rets,"Volatility":vols})
    
    ax = ef.plot.line(x="Volatility", y="Returns", style=style)
    if show_ew : 
        n = er.shape[0]
        w_ew = np.repeat(1/n, n)
        r_ew = portfolio_return(w_ew, er)
        vol_ew = portfolio_vol(w_ew, cov)
        # display Equally weigthed (EW) portfolio
        ax.plot([vol_ew], [r_ew], color="goldenrod", marker="o", linestyle="dashed", markersize = 10, linewidth = 2)
    if show_gmv : 
        w_gmv = gmv(cov)
        r_gmv = portfolio_return(w_gmv, er)
        vol_gmv = portfolio_vol(w_gmv, cov)
        # display Global Minimum Variance (GMV) portfolio
        ax.plot([vol_gmv], [r_gmv], color="midnightblue", marker="o", linestyle="dashed", markersize = 10, linewidth = 2)
    if show_cml : 
        ax.set_xlim(left = 0)
        rf = 0.1
        w_msr = msr(riskfree_rate, er, cov)
        r_msr = portfolio_return(w_msr, er)
        vol_msr = portfolio_vol(w_msr, cov)
        # add CML - Capital Market line
        cml_x = [0,vol_msr]
        cml_y = [riskfree_rate,r_msr]
        ax.plot(cml_x, cml_y, color="green", marker="o", linestyle="dashed", markersize = 12, linewidth = 2)
        
        return ax

def run_cppi(risky_r, safe_r=None, m=3, start = 1000, floor=0.8, riskfree_rate=0.03, drawdown = None):
    """
    Run the backtest of the CPPI strategy, given a set of returns for a the risky asset
    Returns a dictionnay containing : Asset value history, Risk Budget History, Risky weight History
    """
    # set up the CPPI parameters
    dates = risky_r.index
    n_steps = len(dates)
    account_value = start
    floor_value = start*floor
    peak = start
    
    if isinstance(risky_r, pd.Series):
        risky_r = pd.DataFrame(risky_r, columns=["R"])
        
    if safe_r is None:
        # Safe Asset with same shape trick
        safe_r = pd.DataFrame().reindex_like(risky_r)
        safe_r.values[:] = riskfree_rate/12 #fast way to set all values to a number

    # set up some DataFrames for saving intermediate values
    account_history = pd.DataFrame().reindex_like(risky_r)
    cushion_history = pd.DataFrame().reindex_like(risky_r)
    risky_w_history = pd.DataFrame().reindex_like(risky_r)

    for step in range(n_steps):
        if drawdown is not None:
            peak = np.maximum(peak, account_value)
            floor_value = peak*(1-drawdown)
        ## CCPI computation
        cushion = (account_value - floor_value)/account_value
        risky_w = m * cushion
        risky_w = np.minimum(risky_w, 1) # no leverage
        risky_w = np.maximum(risky_w, 0) # no short
        safe_w = 1 - risky_w
        risky_alloc = account_value*risky_w # dollar value
        safe_alloc = account_value*safe_w # dollar value
        ## update the account value for this time step
        account_value = risky_alloc*(1+risky_r.iloc[step]) + safe_alloc*(1+safe_r.iloc[step])
        ## save the value so we can look at the history and plot it etc
        cushion_history.iloc[step] = cushion
        risky_w_history.iloc[step] = risky_w
        account_history.iloc[step] = account_value

    risky_wealth = start*(1+risky_r).cumprod()
    backtest_result = {
        "Wealth": account_history,
        "Risky Wealth": risky_wealth, 
        "Risky Budget": cushion_history, 
        "Risky Allocation": risky_w_history, 
        "multiplier": m,
        "start": start,
        "floor": floor, 
        "risky_r": risky_r, 
         "safe_r": safe_r
    }
    return backtest_result
    
def summary_stats(r, riskfree_rate = 0.03):
    """
    Return a DataFrame that contains aggregated summary stats for the returns in the columns of r
    """
    ann_r = r.aggregate(annualize_rets,periods_per_year=12)
    ann_vol = r.aggregate(annualize_vol,periods_per_year=12)
    ann_sr = r.aggregate(sharpe_ratio,riskfree_rate=riskfree_rate,periods_per_year=12)
    dd = r.aggregate(lambda r:drawdown(r).Drawdown.min())
    skew = r.aggregate(skewness)
    kurt = r.aggregate(kurtosis)
    cf_var5 = r.aggregate(var_gaussian, modified=True) # Cornish-Fisher VaR
    hist_cvar5 = r.aggregate(cvar_historic)
    
    return pd.DataFrame({
        "Annualized Return": ann_r,
        "Annualized Vol": ann_vol,
        "Skewness": skew,
        "Kurtosis": kurt,
        "Cornish-Fisher VaR (5%)": cf_var5,
        "Historic CVaR (5%)": hist_cvar5,
        "Sharpe Ratio": ann_sr,
        "Max Drawdown": dd
    })
    
def gbm_mag(n_years=10, n_scenarios=1000, mu = 0.07, sigma=0.15, steps_per_year=12, s_0 = 100.0):
    """
    Evolution of a stock Price using a geometric Brownian Motion Model
    """
    dt = 1/steps_per_year
    n_steps = int(n_years * steps_per_year)
    #less loop thus efficience
    rets_plus_1 = np.random.normal(loc=1+mu*dt,scale=sigma*np.sqrt(dt),size=(n_steps, n_scenarios)) 
    rets_plus_1[0] = 1 # first raw to 1 aka return to 0
    # to prices
    prices = s_0*pd.DataFrame(rets_plus_1).cumprod()
    return prices

def gbm(n_years = 10, n_scenarios=1000, mu=0.07, sigma=0.15, steps_per_year=12, s_0=100.0, prices=True):
    """
    Evolution of Geometric Brownian Motion trajectories, such as for Stock Prices through Monte Carlo
    :param n_years:  The number of years to generate data for
    :param n_paths: The number of scenarios/trajectories
    :param mu: Annualized Drift, e.g. Market Return
    :param sigma: Annualized Volatility
    :param steps_per_year: granularity of the simulation
    :param s_0: initial value
    :return: a numpy array of n_paths columns and n_years*steps_per_year rows
    """
    # Derive per-step Model Parameters from User Specifications
    dt = 1/steps_per_year
    n_steps = int(n_years*steps_per_year) + 1
    # the standard way ...
    # rets_plus_1 = np.random.normal(loc=mu*dt+1, scale=sigma*np.sqrt(dt), size=(n_steps, n_scenarios))
    # without discretization error ...
    rets_plus_1 = np.random.normal(loc=(1+mu)**dt, scale=(sigma*np.sqrt(dt)), size=(n_steps, n_scenarios))
    rets_plus_1[0] = 1
    ret_val = s_0*pd.DataFrame(rets_plus_1).cumprod() if prices else rets_plus_1-1
    return ret_val

def show_gbm(n_scenarios, mu, sigma):
    """
    Draw the results of a stock price evolution under a Geometric Brownian motion model (GBM)
    """
    s_0 = 100
    prices = gbm(n_scenarios=n_scenarios, mu=mu, sigma=sigma, s_0 = s_0)
    ax = prices.plot(legend=False, color="indianred", alpha=0.5, linewidth=2, figsize=(12,5))
    ax.axhline(y=s_0, ls=":", color="black")
    # ax.set_ylim(top=400)
    # draw a dot at the origin
    ax.plot(0,s_0, marker="o", color="darkred", alpha=0.2)

import matplotlib.pyplot as plt
import numpy as np

def show_cppi(n_scenarios=50, mu=0.07, sigma=0.15, m=3, floor=0., riskfree_rate=0.03, y_max=100, steps_per_year=12):
    """
    Plot the results of a Monte Carlo Simulation of CPPI
    """
    start = 100
    sim_rets = gbm(n_scenarios=n_scenarios, mu=mu, sigma=sigma, prices=False, steps_per_year=steps_per_year)
    risky_r = pd.DataFrame(sim_rets)
    #ru the "back"-test
    btr = run_cppi(risky_r=pd.DataFrame(risky_r), riskfree_rate=riskfree_rate, m=m, start=start, floor=floor)
    wealth = btr["Wealth"]
    
    # calculate terminal weath stats
    y_max = wealth.values.max()*y_max/100
    terminal_wealth = wealth.iloc[-1]
    
    tw_mean = terminal_wealth.mean()
    tw_median = terminal_wealth.median()
    failure_mask = np.less(terminal_wealth, start*floor)
    n_failures = failure_mask.sum()
    p_fail = n_failures / n_scenarios
    
    # use of dot product with np.dot , sum of product
    e_shortfall = np.dot(terminal_wealth - start*floor, failure_mask)/n_failures if n_failures > 0 else 0.0
    
    # Plot !
    fig, (wealth_ax, hist_ax) = plt.subplots(nrows=1, ncols=2, sharey=True, gridspec_kw={'width_ratios':[3,2]}, 
                                             figsize = (24,9))
    plt.subplots_adjust(wspace=0.0)
    
    
    wealth.plot(ax = wealth_ax, legend=False, alpha=0.3, color="indianred", figsize=(12,6))
    wealth_ax.axhline(y=start, ls=":", color="black")
    wealth_ax.axhline(y=start*floor, ls="--", color="red")
    wealth_ax.set_ylim(top=y_max)
    
    terminal_wealth.plot.hist(ax=hist_ax, bins=50, ec='w', fc='indianred', orientation='horizontal')
    hist_ax.axhline(y=start, ls=":", color="black")
    hist_ax.axhline(y=tw_mean, ls=":", color="blue")
    hist_ax.axhline(y=tw_median, ls=":", color="purple")
    
    hist_ax.annotate(f"Mean: ${int(tw_mean)}", xy=(.7, .9), xycoords="axes fraction", fontsize=24)
    hist_ax.annotate(f"Median: ${int(tw_median)}", xy=(.7, .8), xycoords="axes fraction", fontsize=24)
    if (floor > 0.01):
        hist_ax.axhline(y=start*floor, ls="--", color="red", linewidth=3)
        hist_ax.annotate(f"Violations: {n_failures} ({p_fail*100:2.2f}%)\nE(shortfall)=${e_shortfall:2.2f}", xy=(.7, .60),
                         xycoords="axes fraction", fontsize=20)
        
def discount_vOld(t,r):
    """
    Compute the price of a pure discount bond that pays a dollar at time t, diven the interest rate r
    """
    return (1+r)**(-t)

def discount(t,r):
    """
    Compute the price of a pure discount bond that pays a dollar at time period t,
    and r is the per-period interest rate
    returns a |t[ x |r| Series or DataFrame
    r can be a float, Series or DataFrame
    returns a DataFrame indexed by t
    """
    discounts = pd.DataFrame([(1+r)**(-i) for i in t])
    discounts.index = t
    return discounts

def pv_vOld(l, r):
    """
    Computes the present value of a sequence of liabilities
    l is indexed by the time, and the values are the amounts of each liability
    returns the present value of the sequence
    """
    dates = l.index
    discounts = discount(dates, r)
    return (discounts*l).sum()

def pv(flows, r):
    """
    Computes the present value of a sequence of a sequence of cash flows given by the time (as an index) and amoutns 
    r can be a scalar, Or a Series or a DataFrame with the number of rows matching the num of rows in flows
    """
    dates = flows.index
    discounts = discount(dates, r)
    return discounts.multiply(flows, axis='rows').sum()

def funding_ratio(assets, liabilities, r):
    """
    Computes the funding ratio of some assets given liabilities and interest rate
    """
    return pv(assets, r)/pv(liabilities, r)

def inst_to_ann(r):
    """
    Converts short or instant rate to an annualized rate
    """
    # return np.exp(r)-1 #less efficient
    return np.expm1(r)

def ann_to_inst(r):
    """
    Converts annualized rate to a short rate
    """
    # return np.log(1 + r) #less efficient
    return np.log1p(r)

import math

def cir(n_years = 10, n_scenarios=1, a=0.05, b=0.03, sigma=0.05, steps_per_year=12, r_0 = None):
    """
    Generate random interest rate evolutio over time using the CIR model
    b and r_0 are assumed to be annualized rate, not the short rate
    and the returned value are the annualized rates as well
    """
    if r_0 is None: r_0 = b
    r_0 = ann_to_inst(r_0) #convertion of annualized to instant, similar for small value fo r
    dt = 1/steps_per_year
    num_steps = int(n_years*steps_per_year) + 1 # +1 for the initialization and int as n_years might be a float
    
    shock = np.random.normal(0, scale=np.sqrt(dt), size=(num_steps, n_scenarios)) #dW_t
    rates = np.empty_like(shock)
    rates[0] = r_0
    
    ## for Price Generation
    h = math.sqrt(a**2 + 2*sigma**2)
    prices = np.empty_like(shock)
    ####
    
    ## define Princing formula
    def price(ttm, r):
        _A = ((2*h*math.exp((h+a)*ttm/2))/(2*h + (h+a)*(math.exp(h*ttm)-1)))**(2*a*b/sigma**2)
        _B = (2*(math.exp(h*ttm)-1))/(2*h + (h+a)*(math.exp(h*ttm)-1))
        _P = _A*np.exp(-_B*r)
        return _P
    prices[0] = price(n_years, r_0)
    ####
     
    for step in range(1, num_steps):
        r_t = rates[step-1]
        d_r_t = a*(b-r_t)*dt + sigma*np.sqrt(r_t)*shock[step]
        # rates[step] = r_t + d_r_t original version but the second line make sure that no negative rate
        rates[step] = abs(r_t + d_r_t)
        # generate prices at time t as well ...
        prices[step] = price(n_years-step*dt, rates[step])
    
    rates = pd.DataFrame(data = inst_to_ann(rates), index = range(num_steps))
    ### for prices
    prices = pd.DataFrame(data = prices, index = range(num_steps))
    ##
    return rates, prices

def bonds_cash_flows(maturity, principal=100, coupon_rate=0.03, coupons_per_year=12):
    """
    Returns a series of cash flow generated by a bond, 
    indexed by a coupon number
    """
    n_coupons = round(maturity*coupons_per_year)
    coupon_amt = principal*coupon_rate/coupons_per_year
    coupon_times = np.arange(1,n_coupons+1)
    cash_flows = pd.Series(data=coupon_amt, index = coupon_times)
    cash_flows.iloc[-1] += principal
    return cash_flows

def bonds_price_vOld(maturity, principal=100, coupon_rate=0.03, coupons_per_year=12, discount_rate=0.03):
    """
    Price a bond based on parameters maturity, principal, coupon rate and coupons_per_year
    and the prevailing discount rate
    """
    cash_flows = bonds_cash_flows(maturity, principal, coupon_rate, coupons_per_year)
    return pv(cash_flows, discount_rate/coupons_per_year)

def bonds_price(maturity, principal=100, coupon_rate=0.03, coupons_per_year=12, discount_rate=0.03):
    """
    Computes the price of a bon that pays regular coupons untill maturity
    at which time the principal and the final coupon is returned
    This is not designied to be efficient, rather, 
    it is to illustrate the underlying principle behind bond princing !
    If discount rate is a DataFrame, then this is assumed to be the rate on each coupon date
    and the bond value is computed over time
    i.e. The index of the discount_rate DataFrame is assumed to be the coupon number
    """
    if isinstance(discount_rate, pd.DataFrame):
        pricing_dates = discount_rate.index
        prices = pd.DataFrame(index=pricing_dates, columns=discount_rate.columns)
        for t in pricing_dates:
            prices.loc[t] = bonds_price(maturity-t/coupons_per_year, principal, coupon_rate, coupons_per_year, discount_rate.loc[t])
        return prices
    else: # base case .... single time period
        if maturity <= 0: return principal+principal*coupon_rate/coupons_per_year
        cash_flows = bonds_cash_flows(maturity, principal, coupon_rate, coupons_per_year)
        return pv(cash_flows, discount_rate/coupons_per_year)

def macaulay_duration_mag(flows, discount_rate):
    """
    Computes the Macaulay duration of a sequence of cash flows
    """
    discounted_flows = discount(flows.index, discount_rate)*flows
    weights = discounted_flows/discounted_flows.sum()
    return np.average(pd.DataFrame(flows.index), weights=weights, axis='rows') # weighted average

def macaulay_duration(flows, discount_rate):
    """
    Computes the Macaulay Duration of a sequence of cash flows, given a per-period discount rate
    """
    discounted_flows = discount(flows.index, discount_rate)*pd.DataFrame(flows)
    weights = discounted_flows/discounted_flows.sum()
    return np.average(flows.index, weights=weights.iloc[:,0])

def match_durations(cf_t, cf_s, cf_l, discount_rate):
    """
    Returns the weight W in cf_s that along with (1-w) in cf_l will have an effective duration that matched cf_t
    there is an implicite hyptothesis that both cash flows have the same coupon per year 
        --> over wise duration is expressed in number of period and need to be devided by coupons_per_year
        --> code need updates to consider the coupons_per_year
    """
    d_t = macaulay_duration(cf_t, discount_rate)
    d_s = macaulay_duration(cf_s, discount_rate)
    d_l = macaulay_duration(cf_l, discount_rate)
    return (d_l - d_t)/(d_l - d_s)

def bond_total_return(monthly_prices, principal, coupon_rate, coupons_per_year):
    """
    Computes the total return of a bond based on amonthly bonds prices and coupon payments
    Assumes that dividends (coupons) are paid out at the end of the periods (e.g end of 3 months for a quarterly div)
    and that dividends are reinvested in the bonds
    """
    coupons = pd.DataFrame(data = 0, index = monthly_prices.index, columns = monthly_prices.columns)
    t_max = monthly_prices.index.max()
    pay_date = np.linspace(12/coupons_per_year, t_max, int(coupons_per_year*t_max/12), dtype=int)
    coupons.iloc[pay_date] = principal*coupon_rate/coupons_per_year
    total_returns = (monthly_prices+coupons)/monthly_prices.shift()-1
    return total_returns.dropna()

def bt_mix(r1, r2, allocator, **kwargs):
    """
    Runs a back test (simulation) of allocating between a two sets of returns
    r1 and r2 are T x N dataframe or returns where T is the time step index and N is the number of scenarios
    Allocator is a function that takes two sets of returns and allocator specific parameters, an produces
    an allocation to the first portfolio (the rest of the money is invested in the GHP) as a T x 1 DataFrame
    Returns a T x N DataFrame  of the resulting N portfolio scenarios
    """
    if not r1.shape == r2.shape:
        raise ValueError("r1 and r2 need to be the same shape")
    weights = allocator(r1, r2, **kwargs)
    if not weights .shape == r1.shape:
        raise ValueError("Allocator returned weights that don't match r1")
    r_mix = weights*r1 + (1-weights)*r2
    return r_mix

def fixedmix_allocator(r1, r2, w1, **kwargs):
    """
    Produces a time series over T steps of allocations between the PSP and GHP across N scenarios
    PSP and GHP are T x N dataFrames that represent the returns of the PSP and GHP such that:
        each column is a scenario
        each row is the price for a timestep
    return an T x N DataFrame of the PSP weights
    """
    return pd.DataFrame(data=w1, index = r1.index, columns=r1.columns)

def terminal_values(rets):
    """
    Returns the final values of a dollat at the end of the return period for each scenario
    """
    return (rets+1).prod()
def terminal_stats(rets, floor=0.8, cap=np.inf, name="Stats"):
    """
    Produce the Summary Satistics on the terminal values per invester dollar
    across a range of N scenarios
    rets is a T x N DataFrame of returns, where T is the time-step (we assume rets is sorted by time)
    Returns a 1 column Dataframe of summary stats indexed by the stat name
    """
    terminal_wealth = (1+rets).prod()
    breach = terminal_wealth < floor
    reach = terminal_wealth >= cap
    p_breach = breach.mean() if breach.sum() > 0 else np.nan
    p_reach = reach.mean() if reach.sum() > 0 else np.nan
    e_short = (floor - terminal_wealth[breach]).mean() if breach.sum() > 0 else np.nan
    e_surplus = (cap - terminal_wealth[reach]).mean() if reach.sum() > 0 else np.nan
    sum_stats = pd.DataFrame.from_dict({
        "mean": terminal_wealth.mean(),
        "std": terminal_wealth.std(),
        "p_breach": p_breach ,
        "e_short": e_short, 
        "p_reach": p_reach,
        "e_surplus": e_surplus,
    }, orient = "index", columns=[name])
    return sum_stats

def glidepath_allocator(r1, r2, start_glide=1, end_glide=0):
    """
    Simulates a Target-Date-Fund style gradual move from r1 to r2
    """
    n_points = r1.shape[0]
    n_col = r1.shape[1]
    path = pd.Series(data = np.linspace(start_glide, end_glide, num=n_points))
    paths = pd.concat([path]*n_col, axis = 1)
    paths.index = r1.index
    paths.columns = r1.columns
    return paths

def floor_allocator(psp_r, ghp_r, floor, zc_prices, m=3):
    """
    Allocated between the PSP and GHP woth the gpal to provide exposure to the upside
    of the PSP without going violating the floor
    Uses a CPPI-style dynamic risk budgeting algorithm by investing a multiple
    of the cushion in the PSP
    Returns a DataFrame with the same shape as the psp/ghp representing the weights in the PSP
    """
    if zc_prices.shape != psp_r.shape:
        raise ValueError("PSP and ZC prices must have the same shape")
    n_steps, n_scenarios = psp_r.shape
    account_value = np.repeat(1, n_scenarios)
    floor_value = np.repeat(1, n_scenarios)
    w_history = pd.DataFrame(index=psp_r.index, columns = psp_r.columns)
    for step in range(n_steps):
        floor_value = floor*zc_prices.iloc[step] ## PV of floor assuming today's rates and flat YC
        cushion = (account_value - floor_value)/account_value
        psp_w = (m*cushion).clip(0,1) # .clip(0,1) is same as applying mix and max
        ghp_w = 1-psp_w
        psp_alloc = account_value*psp_w
        ghp_alloc = account_value*ghp_w
        # recompute the new account value at the end of this step
        account_value = psp_alloc*(1+psp_r.iloc[step]) + ghp_alloc*(1+ghp_r.iloc[step])
        w_history.iloc[step] = psp_w
    return w_history

def drawdown_allocator(psp_r, ghp_r, maxdd, m=3):
    """
    Allocated between the PSP and GHP woth the gpal to provide exposure to the upside
    of the PSP without going violating the floor
    Uses a CPPI-style dynamic risk budgeting algorithm by investing a multiple
    of the cushion in the PSP
    Returns a DataFrame with the same shape as the psp/ghp representing the weights in the PSP
    """
    n_steps, n_scenarios = psp_r.shape
    account_value = np.repeat(1, n_scenarios)
    floor_value = np.repeat(1, n_scenarios)
    peak_value = np.repeat(1, n_scenarios) ## new line compared to floor allocator
    w_history = pd.DataFrame(index=psp_r.index, columns = psp_r.columns)
    for step in range(n_steps):
        floor_value = (1-maxdd)*peak_value ## floor is based on the prev peak
        cushion = (account_value - floor_value)/account_value
        psp_w = (m*cushion).clip(0,1) # .clip(0,1) is same as applying mix and max
        ghp_w = 1-psp_w
        psp_alloc = account_value*psp_w
        ghp_alloc = account_value*ghp_w
        # recompute the new account value at the end of this step
        account_value = psp_alloc*(1+psp_r.iloc[step]) + ghp_alloc*(1+ghp_r.iloc[step])
        peak_value = np.maximum(peak_value, account_value) 
        w_history.iloc[step] = psp_w
    return w_history














