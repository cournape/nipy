# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
This module defines some convenience functions of time.

linear_interp : a Formula for a linearly interpolated function of time

step_function : a Formula for a step function of time

events : a convenience function to generate sums of events

blocks : a convenience function to generate sums of blocks

convolve_functions : numerically convolve two functions of time

fourier_basis : a convenience function to generate a Fourier basis

"""

__docformat__ = 'restructuredtext'

import numpy as np
import numpy.fft as FFT
from scipy.interpolate import interp1d

from sympy import DiracDelta, Symbol 
from sympy import sin as sympy_sin
from sympy import cos as sympy_cos
from sympy import pi as sympy_pi

from . import formula
from .aliased import aliased_function, vectorize


t = formula.Term('t')


def fourier_basis(freq):
    """
    Formula for Fourier drift, consisting of sine and
    cosine waves of given frequencies.

    Parameters
    ----------

    freq : [float]
        Frequencies for the terms in the Fourier basis.

    Outputs
    -------

    f : Formula

    Examples
    --------
    
    >>> f=fourier_basis([1,2,3])
    >>> f.terms
    array([cos(2*pi*t), sin(2*pi*t), cos(4*pi*t), sin(4*pi*t), cos(6*pi*t),
           sin(6*pi*t)], dtype=object)
    >>> f.mean
    _b0*cos(2*pi*t) + _b1*sin(2*pi*t) + _b2*cos(4*pi*t) + _b3*sin(4*pi*t) + _b4*cos(6*pi*t) + _b5*sin(6*pi*t)
    >>>               
    """

    r = []
    for f in freq:
        r += [sympy_cos((2*sympy_pi*f*t)),
              sympy_sin((2*sympy_pi*f*t))]
    return formula.Formula(r)


def linear_interp(times, values, fill=0, name=None, **kw):
    """ Linear interpolation function of t given `times` and `values`

    Imterpolator such that:
    
    f(times[i]) = values[i]

    if t < times[0]:
        f(t) = fill

    Parameters
    ----------
    times : ndarray
        Increasing sequence of times
    values : ndarray
        Values at the specified times
    fill : float, optional
        Value on the interval (-np.inf, times[0]). Default 0.
    name : None or str, optional
        Name of symbolic expression to use. If None, a default is used.
    **kw : keyword args, optional
        passed to ``interp1d``
        
    Returns
    -------
    f : sympy expression 
        A Function of t.

    Examples
    --------
    >>> s=linear_interp([0,4,5.],[2.,4,6], bounds_error=False)
    >>> tval = np.array([-0.1,0.1,3.9,4.1,5.1]).view(np.dtype([('t', np.float)]))
    >>> s.design(tval)
    array([(nan,), (2.0499999999999998,), (3.9500000000000002,),
           (4.1999999999999993,), (nan,)],
          dtype=[('interp0(t)', '<f8')])
    """
    # XXX - does interpolation have to be linear?
    kw['kind'] = 'linear'
    interp = interp1d(times, values, **kw)
    # make a new name if none provided
    if name is None:
        name = 'interp%d' % linear_interp.counter
        linear_interp.counter += 1
    s = aliased_function(name, interp)
    return s(t)
linear_interp.counter = 0


def step_function(times, values, name=None, fill=0):
    """
    Right-continuous step function such that

    f(times[i]) = values[i]

    if t < times[0]:
        f(t) = fill

    Parameters
    ----------
    times : ndarray
        Increasing sequence of times
    values : ndarray
        Values at the specified times
    fill : float
        Value on the interval (-np.inf, times[0])
    name : str
        Name of symbolic expression to use. If None,
        a default is used.

    Returns
    -------
    f : Formula
        A Formula with only a step function, as a function of t.

    Examples
    --------
    
    >>> s=step_function([0,4,5],[2,4,6])
    >>> tval = np.array([-0.1,3.9,4.1,5.1]).view(np.dtype([('t', np.float)]))
    >>> s.design(tval)
    array([(0.0,), (2.0,), (4.0,), (6.0,)],
          dtype=[('step0(t)', '<f8')])
    >>>

    """
    times = np.asarray(times)
    values = np.asarray(values)        

    def anon(x, times=times, values=values, fill=fill):
        d = values[1:] - values[:-1]
        f = np.less(x, times[0]) * fill + np.greater(x, times[0]) * values[0]
        for i in range(d.shape[0]):
            f = f + np.greater(x, times[i+1]) * d[i]
        return f

    if name is None:
        name = 'step%d' % step_function.counter
        step_function.counter += 1

    s = aliased_function(name, anon)
    return s(t)

# Initialize counter for step function
step_function.counter = 0


def events(times, amplitudes=None, f=DiracDelta, g=Symbol('a')):
    """
    Return a sum of functions based on a sequence of times.

    Parameters
    ----------
    times : sequence
       vector of onsets length $N$
    amplitudes : None or sequence length $N$, optional
        Optional sequence of amplitudes. None (default) results in
        sequence length $N$ of 1s
    f : sympy.Function, optional
        Optional function. Defaults to DiracDelta, can be replaced with
        another function, f, in which case the result is the convolution
        with f.
    g : sympy.Basic, optional
        Optional sympy expression function of amplitudes.  The
        amplitudes, should be represented by the symbol 'a', which
        will be substituted, by the corresponding value in
        `amplitudes`. .

    Returns
    -------
    sum_expression : Sympy.Add
        Sympy expression of time $t$, where onsets, as a function of
        $t$, have been symbolically convolved with function `f`, and any
        function `g` of corresponding amplitudes.

    Examples
    --------
    >>> events([3,6,9])
    DiracDelta(-9 + t) + DiracDelta(-6 + t) + DiracDelta(-3 + t)
    >>> h = Symbol('hrf')
    >>> events([3,6,9], f=h)
    hrf(-9 + t) + hrf(-6 + t) + hrf(-3 + t)

    >>> events([3,6,9], amplitudes=[2,1,-1])
    -DiracDelta(-9 + t) + 2*DiracDelta(-3 + t) + DiracDelta(-6 + t)

    >>> b = [Symbol('b%d' % i, dummy=True) for i in range(3)]
    >>> a = Symbol('a')
    >>> p = b[0] + b[1]*a + b[2]*a**2
    >>> events([3,6,9], amplitudes=[2,1,-1], g=p)
    (2*_b1 + 4*_b2 + _b0)*DiracDelta(-3 + t) + (-_b1 + _b0 + _b2)*DiracDelta(-9 + t) + (_b0 + _b1 + _b2)*DiracDelta(-6 + t)

    >>> h = Symbol('hrf')
    >>> events([3,6,9], amplitudes=[2,1,-1], g=p, f=h)
    (2*_b1 + 4*_b2 + _b0)*hrf(-3 + t) + (-_b1 + _b0 + _b2)*hrf(-9 + t) + (_b0 + _b1 + _b2)*hrf(-6 + t)
    """
    e = 0
    asymb = Symbol('a')
    if amplitudes is None:
        def _amplitudes():
            while True:
                yield 1
        amplitudes = _amplitudes()
    for _t, a in zip(times, amplitudes):
        e = e + g.subs(asymb, a) * f(t-_t)
    return e


def blocks(intervals, amplitudes=None, g=Symbol('a')):
    """
    Return a step function
    based on a sequence of intervals.

    Inputs:
    =======

    intervals : [(float, float)]
        "On" intervals for the block.

    amplitudes : [float]
        Optional amplitudes for each block. Defaults to 1.

    g : sympy.Basic
        Optional sympy expression function involving 'a', which
        will be substituted for 'a' in the generator.

    Examples:
    =========
    
    >>> tval = np.array([0.4,1.4,2.4,3.4]).view(np.dtype([('t', np.float)]))
    >>> b = blocks([[1,2],[3,4]])
    >>> b.design(tval)
    array([(0.0,), (1.0,), (0.0,), (1.0,)], 
          dtype=[('step0(t)', '<f8')])

    >>> b = blocks([[1,2],[3,4]], amplitudes=[3,5])
    >>> b.design(tval)
    array([(0.0,), (3.0,), (0.0,), (5.0,)], 
          dtype=[('step1(t)', '<f8')])

    >>> a = Symbol('a')
    >>> b = blocks([[1,2],[3,4]], amplitudes=[3,5], g=a+1)
    >>> b.design(tval)
    array([(0.0,), (4.0,), (0.0,), (6.0,)], 
          dtype=[('step2(t)', '<f8')])

    """
    t = [-np.inf]
    v = [0]
    asymb = Symbol('a')
    if amplitudes is None:
        def _amplitudes():
            while True:
                yield 1
        amplitudes = _amplitudes()

    for _t, a in zip(intervals, amplitudes):
        t += list(_t)
        v += [g.subs(asymb, a), 0]

    t.append(np.inf)
    v.append(0)

    return step_function(t, v)


def convolve_functions(fn1, fn2, interval, dt, padding_f=0.1, name=None):
    """
    Convolve fn1 with fn2.
    
    Parameters
    ----------
    fn1 : sympy expr
        An expression that is a function of t only.
    fn2 : sympy expr
        An expression that is a function of t only.
    interval : [float, float]
        The interval over which to convolve the two functions.
    dt : float
        Time step for discretization 
    padding_f : float, optional
        Padding added to the left and right in the convolution.
    name : None or str, optional
        Name of the convolved function in the resulting expression. 
        Defaults to one created by linear_interp.
            
    Returns
    -------
    f : sympy expr
            An expression that is a function of t only.

    Examples
    --------
    >>> import sympy
    >>> t = sympy.Symbol('t')
    >>> # This is a square wave on [0,1]
    >>> f1 = (t > 0) * (t < 1)
    >>> # The convolution of with itself is a triangular wave on [0,2], peaking at 1 with height 1
    >>> tri = convolve_functions(f1, f1, [0,2], 1.0e-03, name='conv')
    >>> print tri
    conv(t)
    >>> ftri = vectorize(tri)
    >>> x = np.linspace(0,2,11)
    >>> y = ftri(x)
    >>> # This is the resulting y-value (which seem to be numerically off by dt
    >>> y
    array([ -3.90255908e-16,   1.99000000e-01,   3.99000000e-01,
           5.99000000e-01,   7.99000000e-01,   9.99000000e-01,
           7.99000000e-01,   5.99000000e-01,   3.99000000e-01,
           1.99000000e-01,   6.74679706e-16])
    >>> 
    """

    max_interval, min_interval = max(interval), min(interval)
    ltime = max_interval - min_interval
    time = np.arange(min_interval, max_interval + padding_f * ltime, dt)

    f1 = vectorize(fn1)
    f2 = vectorize(fn2)
    _fn1 = np.array(f1(time))
    _fn2 = np.array(f2(time))

    _fft1 = FFT.rfft(_fn1)
    _fft2 = FFT.rfft(_fn2)

    value = FFT.irfft(_fft1 * _fft2) * dt
    _minshape = min(time.shape[0], value.shape[-1])
    time = time[0:_minshape]
    value = value[0:_minshape]

    return linear_interp(time + min_interval, value, bounds_error=False, name=name)
