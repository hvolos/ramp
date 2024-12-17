import matplotlib
import matplotlib.pyplot as plt
import functools
import math
import numpy as np
import sys
import decimal
from matplotlib.ticker import FixedLocator, FixedFormatter

decimal.getcontext().prec = 100

def Aj(n,t,j):
    return decimal.Decimal(math.comb(n,j))/decimal.Decimal(n+1)**t

def hamming_bound(t, n):
    s = sum([math.comb(n,k) for k in range(1,t+1)])
    r=1-math.log(s,2)/n
    return r

# RACK-SCALE REDUNDANCY MODEL

# probability to fail when reading a block
#
# b block size
# c cache line size
# p_c probability to fail when reading a cache line
def p_b(b, c, p_c):
    return float(1 - (decimal.Decimal(1)-decimal.Decimal(p_c))**math.ceil(b / c))

class erasure_coding:
    def __init__(self, n_replicas, k_replicas):
        self.n_replicas = n_replicas
        self.k_replicas = k_replicas
        self.m_replicas = n_replicas - k_replicas

    def p_due(self, b, c, p_c):
        n = self.n_replicas
        k = self.k_replicas
        pb = p_b(b, c, p_c)
        return sum([decimal.Decimal(math.comb(n,i))*decimal.Decimal((pb**i)*((1-pb)**(n-i))) for i in range(n-k+1,n+1)])

    def a_r(self, b, c, p_c):
        n = self.n_replicas
        k = self.k_replicas
        fragment_size = b / self.k_replicas
        p_r = p_b(fragment_size, c, p_c)
        return float(-k + sum([decimal.Decimal(math.comb(k+i-1,i))*decimal.Decimal((p_r**i)*((1-p_r)**k)*(k+i)) for i in range(0,n-k+1)]))

class complete_replication:
    def __init__(self, n_replicas):
        self.n_replicas = n_replicas

    def p_due(self, b, c, p_c):
        n = self.n_replicas
        return p_b(b, c, p_c)**n

    def a_r(self, b, c, p_c):
        pb = p_b(b, c, p_c)
        return -1 + sum([decimal.Decimal((pb**i))*decimal.Decimal(1-pb)*(i+1) for i in range(0,self.n_replicas)])

# CHIPKILL MODEL

# probability that a codeword that can correct t bad bits will fail
#
# t maximum number of bad bits
# n codeword length
#
# approximate: usually RBER is small. Then (1-RBER) is about 1 and the first
# term in the sum is dominates, so PCW is proportional to RBER^(E+1)
def p_cw(n, t, rber, approximate=True):
    if approximate:
        return p_cw_approximate(n, t, rber)
    else:
        return p_cw_precise(n, t, rber)

def p_cw_approximate(n, t, rber):
    p = sum([decimal.Decimal(math.comb(n,i))*decimal.Decimal((rber**i)*((1-rber)**(n-i))) for i in range(t+1,t+1+1)])
    return float(p)

def p_cw_precise(n, t, rber):
    p = sum([decimal.Decimal(math.comb(n,i))*decimal.Decimal((rber**i)*((1-rber)**(n-i))) for i in range(t+1,n+1)])
    return float(p)

# Uncorrectable bit error rate
def uber(n, t, rber):
    N = k+r
    return p_cw(t, k, r, rber)/N

# Probability the BCH(n,k,t) codeword will fail
def p_bch(n, k, t, rber):
    return p_cw(n, t, rber, approximate=True)

# Length of BCH codeword to correct t bad bits in k bits of data
def bch_n(k, t):
    return k + int(t * (math.log(k, 2) + 1))

# Maximum number of bad bits we can correct with BCH(n,k)
def bch_t(n, k):
    r = n-k
    return int(r / (math.log(k, 2) + 1))

# Probability of non-detectable error in BCH code
def p_nde_bch_precomputed(n,t,p):
    if (t>23):
        t = 23
    p_nde_given_t = [
        0.3361114337235280921384355159552319115060088614390852881452605853103388383415188468684150512501252808,
        0.2036438478559440347849597419006428461254044377173551437102454011733496950693404593429106096864512981,
        0.01786764133507520478401718934640746856526549185451496209901468588544900855869794906287786711714065428,
        0.0007607062373366267794531576607710063793455635747742779272294452969746959899997478036343465848296790470,
        0.00001905998645679788765110229225647613976652062369186313417371987675993229976612709258075799611231144086,
        3.145458985818853340971764318695412079959861235241652169586415127054332108728301184873650596267331136E-7,
        3.681518426611429889043637904492652141229447264466413636469204335982310341680712650216100245152264514E-9,
        3.219983540629905874033686011566974810528015074037924102372611579044757096463918384931123763987032969E-11,
        2.187984170388904395784961693842440824781935116611404097469894347719289460286376410438065135642518648E-13,
        1.190233209817337214156184021709291521054237395219233963110480364054888483529698835627207835121390534E-15,
        5.308579527734330515280217976935556746657940122889695534688510662185338576809940003829453876849222772E-18,
        1.979305770385003068965370810561645229804831220764037517124748283116376671727619593065672117517324660E-20,
        6.269394424807362704809712474405356260722296336814470539691260834548646960470271513237177735035486261E-23,
        1.710031612438866655299632919317331469597113586075601355131022731704659880858910660863299217063349800E-25,
        4.063256314364930496692546671738595036282245585571803077487959330689460394042246289998563203076739960E-28,
        8.495222703642112314046046938434281099094025081615000380985093177277298769310908287189267090931286226E-31,
        1.576481363265481723545341250537895996747843033398460797575721259759380126435731590671378484957954278E-33,
        2.616635869740421797189493061422252622653786410323139895642228742765843587794249850320826000548171957E-36,
        3.910983818357039732662162703117395774031400595964016592448433725241343599206097656463793856764987836E-39,
        5.295985105715212928526174097094802208817704588898348553745253156478195803265093730399950416548913948E-42,
        6.532591835735009156093637973922057173859567239513449505568876035298388902267619444381301401015636737E-45,
        7.376184494137079018349926095304774590238826912916241115137806529900759199530755668564548919648486994E-48,
        7.658016266032558428052135715145242386778241615441549308619828308669082955874465253351872907650142191E-51,
        7.340024334867337182936222140469734423989576838068997458901723369256354104393700765984242444556011988E-54
    ]
    return p_nde_given_t[t]

def pe(n,w,t):
    numer = 0
    for s in range(0,t+1):
        for j in range(w-s,w+s+1):
            numer = numer + Aj(n,t,j)*decimal.Decimal(math.comb(n-j,math.ceil((s+w-j)/2)))*decimal.Decimal(math.comb(j,math.ceil((s-w+j)/2)))
    return numer/decimal.Decimal(math.comb(n,w))

def p_nde_bch(n,t,p):
    s=0
    for w in range(t+1,n+1-t):
        s = s+decimal.Decimal(math.comb(n,w))*(decimal.Decimal(p)**w)*((1-decimal.Decimal(p))**(n-w))*pe(n,w,t)
    return s

def p_nde_chipkill(n,t,p):
    return p_nde_bch_precomputed(n, t, p)

# probability that the chipkill scheme will fail due to bit errors
def p_chipkill(n, k, t, rber):
    p_rs = 0.018
    return p_rs * p_bch(n, k, t, rber)

def sdc_chipkill(rber):
    t=2
    k=64
    r=8
    n_th = r+1-t
    termA = math.comb(k+r,n_th)*((1-(1-rber)**8)**n_th)*(((1-rber)**8)**(k+r-n_th))
    termB = ((math.comb(k+r,t)*2**(8*t))*(2**(8*k)))/(2**(8*(k+r)))
    return termA*termB

def storage_overhead(n, k):
    r = n-k
    v = r/k + (1+r/k)/8
    return v*100

def storage_overhead_to_n(overhead_perc, k):
    v = overhead_perc / 100
    r = math.ceil((8* v * k-k)/(9))
    return int(r)+k

def plot_failure_vs_overhead(k,rber, replication_scheme):
    temp_xx = np.arange(0., 100.0, 0.1)
    temp_nn = [storage_overhead_to_n(x, k) for x in temp_xx]
    xx = []
    nn = []
    for i in range(0, len(temp_nn)):
        if temp_nn[i] >= k:
            xx.append(temp_xx[i])
            nn.append(temp_nn[i])
    ff = [p_chipkill(n, k, bch_t(n, k), rber) for n in nn]

    fig, ax1 = plt.subplots()

    color = 'tab:red'
    ax1.set_yscale("log")
    ax1.set_ylabel('failure probability', color=color)
    ax1.plot(xx, ff, color=color)
    ax1.set_xlabel('storage overhead')

    color = 'tab:blue'
    ax2 = ax1.twinx()
    ax2.set_ylabel('bandwidth overhead', color=color)
    ax2 = ax2.twiny()

    ax2.set_yscale("log")
    ax2.set_ylim(ax1.get_ylim())

    x_min = ax1.get_xlim()[0]
    x_max = ax1.get_xlim()[1]
    x_len = x_max - x_min
    x_locator = []
    x_formatter = []
    for v in np.arange(xx[0], xx[-1], 10):
        n = storage_overhead_to_n(v, k)
        t = bch_t(n,k)
        x_locator.append((v - x_min)/x_len)
        x_formatter.append(t)
    ax2.xaxis.set_major_locator(FixedLocator(x_locator))
    ax2.xaxis.set_major_formatter(FixedFormatter(x_formatter))
    ax2.set_xlabel('corrected bit errors')

    m = 64
    c = 64
    b = 4096
    pv = [math.ceil(m/b) * replication_scheme.a_r(b, c, p_c) for p_c in ff]

    ax2.plot(xx, pv, color=color)

    plt.show()

def plot_due_vs_storage_overhead(ax, k, rber, b, c):
    temp_xx = np.arange(0., 30, 0.1)
    temp_nn = [storage_overhead_to_n(x, k) for x in temp_xx]
    xx = []
    nn = []
    for i in range(0, len(temp_nn)):
        if temp_nn[i] >= k:
            xx.append(temp_xx[i])
            nn.append(temp_nn[i])
    ff = [p_chipkill(n, k, bch_t(n, k), rber) for n in nn]
    ff_complete = [complete_replication(3).p_due(b, c, p_chipkill(n, k, bch_t(n, k), rber)) for n in nn]
    ff_erasure = [erasure_coding(6,4).p_due(b, c, p_chipkill(n, k, bch_t(n, k), rber)) for n in nn]

    ax.set_yscale("log")
    ax.set_ylabel('DUE')
    ax.plot(xx, ff, linestyle='-', label='Chipkill')
    ax.plot(xx, ff_complete, linestyle='-.', label='Chipkill-REP')
    ax.plot(xx, ff_erasure, linestyle='--', label='Chipkill-EC')
    ax.set_xlabel('Storage Overhead (%)')

    original_chipkill = plt.Rectangle((26.8, 7.7E-33), 0.4, 2*1E-28, color='k', zorder=40)
    ax.add_patch(original_chipkill)

def plot_nde_vs_storage_overhead(ax, k, rber, b, c):
    temp_xx = np.arange(0., 30, 0.1)
    temp_nn = [storage_overhead_to_n(x, k) for x in temp_xx]
    xx = []
    nn = []
    for i in range(0, len(temp_nn)):
        if temp_nn[i] >= k:
            xx.append(temp_xx[i])
            nn.append(temp_nn[i])
    ff = [p_nde_chipkill(n, bch_t(n, k), rber) for n in nn]

    ax.set_yscale("log")
    ax.set_ylabel('NDE')
    ax.plot(xx, ff, linestyle='-', label='Chipkill')
    ax.set_xlabel('Storage Overhead (%)')


def plot_failure_vs_performance_overhead(k, rber, c, b):
    temp_xx = np.arange(0., 20, 0.1)
    temp_nn = [storage_overhead_to_n(x, k) for x in temp_xx]
    xx = []
    nn = []
    for i in range(0, len(temp_nn)):
        if temp_nn[i] >= k:
            xx.append(temp_xx[i])
            nn.append(temp_nn[i])
    ff_erasure = [erasure_coding(6,4).a_r(b, c, p_chipkill(n, k, bch_t(n, k), rber)) for n in nn]
    ff_complete = [complete_replication(3).a_r(b, c, p_chipkill(n, k, bch_t(n, k), rber)) for n in nn]

    fig, ax1 = plt.subplots()

    ax1.set_yscale("log")
    ax1.set_ylabel('Relative Performance Overhead')
    ax1.plot(xx, ff_complete, linestyle='-.', label='Chipkill-REP')
    ax1.plot(xx, ff_erasure, linestyle='--', label='Chipkill-EC')
    ax1.set_xlabel('Storage Overhead (%)')
    ax1.legend()

    plt.show()

def plot_storage_overhead_vs_block_size(ax, k, rber, c, savepdf=None):
    uber = 1E-32
    bb = range(c, 4096*4, c)
    vv_none = [storage_overhead_for_target_uber(k, rber, complete_replication(1), b, c, uber) for b in bb]
    vv_complete = [storage_overhead_for_target_uber(k, rber, complete_replication(3), b, c, uber) for b in bb]
    vv_erasure = [storage_overhead_for_target_uber(k, rber, erasure_coding(6,4), b, c, uber) for b in bb]

    ax.set_ylabel('Storage Overhead (%)')
    ax.plot(bb, vv_none, linestyle='-', label='Chipkill')
    ax.plot(bb, vv_complete, linestyle='-.', label='Chipkill-REP')
    ax.plot(bb, vv_erasure, linestyle='--', label='Chipkill-EC')
    ax.set_xlabel('Block Size (Bytes)')

def plot_storage_overhead_vs_replication_factor(ax, k, rber, b, c, savepdf=None):
    uber = 1E-32
    rr = range(1, 10)
    vv_none = [storage_overhead_for_target_uber(k, rber, complete_replication(1), b, c, uber)]
    vv_rep = [storage_overhead_for_target_uber(k, rber, complete_replication(r), b, c, uber) for r in rr]
    vv_ec = [storage_overhead_for_target_uber(k, rber, erasure_coding(r+4, 4), b, c, uber) for r in rr]
    ax.set_ylabel('Storage Overhead (%)')
    ax.plot([1], vv_none, linestyle='-', marker='+', label='Chipkill')
    ax.plot(rr, vv_rep, linestyle='-.', label='Chipkill-REP')
    ax.plot(rr, vv_ec, linestyle='--', label='Chipkill-EC')
    ax.set_xlabel('# Replicas')


def plot_storage_overhead_vs_rber(ax, k, b, c, savepdf=None):
    rber_range = [10**-2, 10**-3, 10**-4, 10**-5, 10**-6, 10**-7]
    uber = 1E-32
    vv_none = [storage_overhead_for_target_uber(k, rber, complete_replication(1), b, c, uber) for rber in rber_range]
    vv_rep = [storage_overhead_for_target_uber(k, rber, complete_replication(3), b, c, uber) for rber in rber_range]
    vv_ec = [storage_overhead_for_target_uber(k, rber, erasure_coding(6, 4), b, c, uber) for rber in rber_range]
    ax.set_ylabel('Storage Overhead (%)')
    ax.plot(rber_range, vv_none, linestyle='-', marker = '+', label='Chipkill')
    ax.plot(rber_range, vv_rep, linestyle='-.', marker = '+', label='Chipkill-REP')
    ax.plot(rber_range, vv_ec, linestyle='--', marker = '+', label='Chipkill-EC')
    ax.set_xlabel('RBER')
    ax.set_xscale('log') 

def storage_overhead_for_target_uber(k, rber, replication_scheme, b, c, uber):
    for t in range(0,40,1):
        n = bch_n(k, t)
        v = storage_overhead(n,k)
        p_c = p_chipkill(n, k, t, rber)
        p_due = replication_scheme.p_due(b, c, p_c)
        if p_due < uber:
            return v
    return None

def print_p_due(k, rber, replication_scheme, b, c):
    print('n', 'k', 't', 'storage_overhead', 'p_c', 'p_due', 'bandwidth_overhead')
    for t in range(0,23,1):
        n = bch_n(k, t)
        v = storage_overhead(n,k)
        p_c = p_chipkill(n, k, t, rber)
        p_due = replication_scheme.p_due(b, c, p_c)
        a_r = replication_scheme.a_r(b, c, p_c)
        bw_overhead = a_r
        print(n, k, t, v, p_c, p_due, bw_overhead)

def plot_overhead_onefigure():
    b = 4096
    c = 64
    matplotlib.rcParams.update({'font.size': 14})
    fig = plt.figure()
    fig.set_figwidth(10)
    fig.set_figheight(10)
    axes = []
    axes.append(fig.add_axes([0.1, 0.44 , 0.38, 0.25, ]))
    axes.append(fig.add_axes([0.58, 0.44, 0.38, 0.25, ]))
    axes.append(fig.add_axes([0.1, 0.12, 0.38, 0.25, ]))
    axes.append(fig.add_axes([0.58, 0.12, 0.38, 0.25, ]))
    plot_due_vs_storage_overhead(axes[0], k, rber, b, c)
    plot_nde_vs_storage_overhead(axes[1], k, rber, b, c)
    plot_storage_overhead_vs_block_size(axes[2], k, rber, c)
    plot_storage_overhead_vs_replication_factor(axes[3], k, rber, b, c)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=3, loc='lower center', frameon=False)
    plt.tight_layout()
    #plt.show()
    fig.savefig("overhead.pdf")

def plot_overhead_multifigure():
    b = 4096
    c = 64
    matplotlib.rcParams.update({'font.size': 14})

    fig = plt.figure()
    fig.set_figwidth(10)
    fig.set_figheight(5)
    plt.subplots_adjust(bottom=0.2, top=0.9, left=0.1, right=0.9)
    plot_due_vs_storage_overhead(plt.gca(), k, rber, b, c)
    handles, labels = plt.gca().get_legend_handles_labels()
    fig.legend(handles, labels, ncol=3, loc='lower center', frameon=False)
    fig.savefig("due_vs_storage_overhead.pdf")

    fig = plt.figure()
    fig.set_figwidth(10)
    fig.set_figheight(5)
    plt.subplots_adjust(bottom=0.2, top=0.9, left=0.1, right=0.9)
    plot_nde_vs_storage_overhead(plt.gca(), k, rber, b, c)
    handles, labels = plt.gca().get_legend_handles_labels()
    fig.legend(handles, labels, ncol=3, loc='lower center', frameon=False)
    fig.savefig("nde_vs_storage_overhead.pdf")

    fig = plt.figure()
    fig.set_figwidth(10)
    fig.set_figheight(5)
    plt.subplots_adjust(bottom=0.2, top=0.9, left=0.1, right=0.9)
    plot_storage_overhead_vs_replication_factor(plt.gca(), k, rber, b, c)
    handles, labels = plt.gca().get_legend_handles_labels()
    fig.legend(handles, labels, ncol=3, loc='lower center', frameon=False)
    fig.savefig("storage_overhead_vs_replication_factor.pdf")

    fig = plt.figure()
    fig.set_figwidth(10)
    fig.set_figheight(5)
    plt.subplots_adjust(bottom=0.2, top=0.9, left=0.1, right=0.9)
    plot_storage_overhead_vs_rber(plt.gca(), k, b, c)
    handles, labels = plt.gca().get_legend_handles_labels()
    fig.legend(handles, labels, ncol=3, loc='lower center', frameon=False)
    fig.savefig("storage_overhead_vs_rber.pdf")

def print_p_due(k, rber):
    print('n', 'k', 't', 'storage_overhead', 'p_nde')
    for t in range(23,25,1):
        n = bch_n(k, t)
        v = storage_overhead(n,k)
        p_nde = p_nde_bch(n, t, rber)
        print(n, k, t, v, p_nde)

rber = 2*10**-4
k = 256*8

plot_overhead_multifigure()
