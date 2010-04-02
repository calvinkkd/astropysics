#Copyright (c) 2008 Erik Tollerud (etolleru@uci.edu) 

"""

======
coords
======

The :mod:`coords` module contains classes and funtions specifying locations of
objects on the sky as well as coordinate converstions and distance computations.

Some of the calculations involved make use of the currently selected cosmology
(see :mod:`astropysics.constants`) and hence may not function as expected if a
particularly strange cosmology is in use.

.. seealso::

   `Kapteyn libraries <http://www.astro.rug.nl/software/kapteyn/index.html>`_
        A set of python libraries with excellent coordinate transform and other
        capabilities.
        
   `Pyephem <http://rhodesmill.org/pyephem/>`_
        A Pythonic implementation of the 
        `xephem <http://www.clearskyinstitute.com/xephem/>`_ ephemerides 
        algorithms. 
        
   `Meeus, Jean H. "Astronomical Algorithms" ISBN 0943396352
   <http://www.willbell.com/MATH/mc1.htm>`_ An authoritative reference on
   coordinates, ephemerides, and related transforms in astronomy
   
   `Standards Of Fundamental Astronomy (SOFA) <http://www.iausofa.org/>`_ The
   IAU reference implementations for coordinates and earth rotation.

.. todo:: more examples


Classes and Inheritance Structure
---------------------------------

.. inheritance-diagram:: astropysics.coords
   :parts: 1

Module API
----------

"""

#TODO: WCSlib or similar support a la Kapteyn?
#TODO: JPL Ephemeris and default ephemeris setting functions

#useful references:
#*http://www.astro.rug.nl/software/kapteyn/index.html
#*"Astronomical Algorithms" by Jean Meeus 
#*"The IAU Resolutions on Astronomical Reference Systems,Time Scales, and Earth 
#  Rotation Models": http://aa.usno.navy.mil/publications/docs/Circular_179.pdf
from __future__ import division,with_statement

from .constants import pi
from .utils import DataObjectRegistry
import numpy as np
_twopi = 2*pi

try:
    #requires Python 2.6
    from abc import ABCMeta
    from abc import abstractmethod
    from abc import abstractproperty
    from collections import Sequence,MutableSequence
except ImportError: #support for earlier versions
    abstractmethod = lambda x:x
    abstractproperty = property
    ABCMeta = type
    class MutableSequence(object):
        __slots__=('__weakref__',) #support for weakrefs as necessary
    class Sequence(object):
        __slots__=('__weakref__',) #support for weakrefs as necessary

#<----------------coordinate classes and related functions------------------>


class AngularCoordinate(object):
    """
    An angular coordinate that on the unit sphere.
    
    Arithmetic operators can be applied to the coordinate, and will be applied 
    directly to the numerical value in radians.  For + and -, two angular 
    coordinates may be used, although for -, an AngularSeperation object will
    be returned.
    """
    import re as _re
    __slots__=('_decval','_range')
    
    __acregex = _re.compile(r'(?:([+-])?(\d+(?:[.]\d*)?)(hours|h|degrees|d|radians|rads|rad|r|:(?=\d+:\d+[.]?\d*$)))?(?:(\d+(?:[.]\d*)?)(m|\'|[:]))?(?:(\d+(?:[.]\d*)?)(s|"|$))?$')
    __decregex = _re.compile(r'[+-]\d+([.]\d*)') 
    
    def __init__(self,inpt=None,sghms=None,range=None,radians=False):
        """
        
        The input parser is very adaptable, and can be in any of the following 
        forms for `inpt`:
        
        * A float value
            if `radians` is True, this will be interpreted as decimal radians,
            otherwise, it is in degrees.
        * A :class:`AngularCoordinate` object
            A copy of the input object will be created.
        * None
            The default of 0 will be used.
        * A 3-tuple
            If `sghms` is True, the tuple will be interpreted as
            (hours,min,sec), otherwise, (degrees,min,sec).
        * A string of the form ##.##
            If `radians` is True, this will be cast to a float and used as
            decimal radians, otherwise, it is in degrees.
        * A string of the form ##.##d or ##.##degrees
            The numerical part will be cast to a float and used as degrees.
        * A string of the form ##.##h or ##.##hours
            The numerical part will be cast to a float and used as hours.
        * A string of the form ##.##radians,##.##rads, or ##.##r
            The numerical part will be cast to a float and used as radians.
        * A string of the form (+/-)##h##m##.##s:
            The numerical parts will be treated as hours,minutes, and seconds.
        * A string of the form (+/-)##d##m##.##s or (+/-)##d##'##.##"
            The numerical parts will be treated as degrees,minutes, and seconds.
        * A string of the form (+/-)##:##:##.## Sexigesimal form
            If `sghms` is None the presence of a a + or - sign idicates that it
            should be interpreted as degreesminutes, and seconds. If the sign is
            absent, the numerical portions will be treated as hours,min,sec.
            thewise, if `sghms` evaluates to True, the numerical parts will be
            treated as hours,minutes, and seconds, and if `sghms` evaluates to
            False, degrees,minutes, and seconds.
        
        :param inpt: The coordinate value -- valid forms are described above.            
        :param sghms: 
            If True, ambiguous sexigesimal inputs should be hours, minutes, and
            seconds instead of degrees,arcmin, and arcsec
        :type sghms: boolean
        :param range: 
            Sets the valid range of coordinates.  Either a
            2-sequence (lowerdegrees,upperdegrees) or None (for no limit)
        :param radians:
            If True, ambiguous inputs are treated as radians rather than
            degrees.
        :type radians: boolean
        
        **Examples**
        
        .. testsetup::
        
            from astropysics.coords import AngularCoordinate
            from math import pi
        
        .. doctest::
        
            >>> ac = AngularCoordinate(2.5)
            >>> print ac
            +2d30'00.00"
            >>> print AngularCoordinate(ac)
            +2d30'00.00"
            >>> print AngularCoordinate(pi,radians=True)
            +180d00.00"
            >>> print AngularCoordinate('12d25m12.5s')
            +12d25'12.50"
            >>> print AngularCoordinate('3:30:30',sghms=True)
            +52d37'30.00"
            >>> print AngularCoordinate('3:30:30',sghms=False)
            +3d30'30.00"
            >>> print AngularCoordinate('-3:30:30',sghms=None)
            -3d30'30.00"
            >>> print AngularCoordinate('+3:30:30',sghms=None)
            +3d30'30.00"
            >>> print AngularCoordinate('3:30:30',sghms=None)
            +52d37'30.00"
        
        """
        from operator import isSequenceType
        
        self._range = None
        
        if isinstance(inpt,AngularCoordinate):
            self._decval = inpt._decval
            self._range = inpt._range
            return
        elif inpt is None:
            self._decval = 0
        elif isinstance(inpt,basestring):
            sinpt = inpt.strip()
            acm = self.__acregex.match(sinpt)
            if acm:
                sgn,dec1,mark1,dec2,mark2,dec3,mark3 = acm.group(1,2,3,4,5,6,7)
                val = (0 if dec1 is None else float(dec1)) + \
                      (0 if dec2 is None else float(dec2)/60) + \
                      (0 if dec3 is None else float(dec3)/3600)
                if sgn == '-':
                    val *= -1
                if mark1 == ':':
                    if sghms is None:
                        if sgn is None:
                            self.hours = val
                        else: #'+' or '-'
                            self.degrees = val
                    elif sghms:
                        self.hours = val
                    else:
                        self.degrees = val
                elif mark1 == 'hours' or mark1 == 'h':
                    self.hours = val
                elif mark1 == 'degrees' or mark1 == 'd':
                    self.degrees = val
                elif mark1 == 'radians' or mark1 == 'rad' or mark1 == 'rads' or mark1=='r':
                    self.radians = val
                else:
                    raise ValueError('invalid or ambiguous string input for AngularCoordinate')
            else:
                decm = self.__decregex.match(sinpt)
                if decm:
                    if radians:
                        self.r = float(decm.group(0))
                    else:
                        self.d = float(decm.group(0))
                else:
                    raise ValueError('Invalid string input for AngularCoordinate: '+inpt)
            
        elif isSequenceType(inpt) and len(inpt)==3:
            self.degminsec = inpt
        elif radians:
            self._decval = float(inpt)
        else:
            from math import radians
            self._decval = radians(inpt)
            
        self.range = range
    
    def _setDegminsec(self,dms):
        if not hasattr(dms, '__iter__') or len(dms)!=3:
            raise ValueError('Must set degminsec as a length-3 iterator')
        self.degrees=abs(dms[0])+abs(dms[1])/60.+abs(dms[2])/3600.
        if dms[0]<0:
            self._decval*=-1
    def _getDegminsec(self):
        fulldeg=abs(self.degrees)
        deg=int(fulldeg)
        fracpart=fulldeg-deg
        min=int(fracpart*60.)
        sec=fracpart*3600.-min*60.
        return -deg if self.degrees < 0 else deg,min,sec
    degminsec = property(_getDegminsec,_setDegminsec,doc="""
    The value of this :class:`AngularCoordinate` as an (degrees,minutes,seconds)
    tuple, with degrees and minutes as integers and seconds as a float.    
    """)
    dms = degminsec
    
    def _setHrsminsec(self,dms):
        if not hasattr(dms, '__iter__') or len(dms)!=3:
            raise ValueError('Must set hrsminsec as a length-3 iterator')
        self.degrees=15*(dms[0]+dms[1]/60.+dms[2]/3600.)
    def _getHrsminsec(self):
        factorized=self.degrees/15.
        hrs=int(factorized)
        mspart=factorized-hrs
        min=int(mspart*60.)
        sec=mspart*3600.-min*60.
        return hrs,min,sec
    hrsminsec = property(_getHrsminsec,_setHrsminsec,doc="""
    The value of this :class:`AngularCoordinate` as an (hours,minutes,seconds)
    tuple, with hours and minutes as integers and seconds as a float.    
    """)
    hms = hrsminsec
    
    def _setDecdeg(self,deg):
        rads = deg*pi/180.
        if self.range is not None:
            self._checkRange(rads)
        self._decval = rads
    def _getDecdeg(self):
        return self._decval*180/pi
    degrees = property(_getDecdeg,_setDecdeg,doc="""
    The value of this :class:`AngularCoordinate` in decimal degrees.   
    """)
    d = degrees    
    
    def _setRad(self,rads):
        if self.range is not None:
            self._checkRange(rads)
        self._decval = rads
    def _getRad(self):
        return self._decval
    radians = property(_getRad,_setRad,doc="""
    The value of this :class:`AngularCoordinate` in decimal radians.   
    """)
    r = radians
    
    def _setDechr(self,hr):
        rads = hr*pi/12
        if self.range is not None:
            self._checkRange(rads)
        self._decval = rads
    def _getDechr(self):
        return self._decval*12/pi
    hours = property(_getDechr,_setDechr,doc="""
    The value of this :class:`AngularCoordinate` in decimal hours.   
    """)
    h = hours
    
    def _checkRange(self,rads):
        if self._range is not None:
            low,up = self._range
            if not low <= rads <= up:
                raise ValueError('Attempted to set angular coordinate outside range')
    def _setRange(self,newrng):
        oldrange = self._range        
        try:
            if newrng is None:
                self._range = None
            else:
                from math import radians
                newrng = tuple(newrng)
                if len(newrng) != 2:
                    raise ValueError('range is not a 2-sequence')
                elif newrng[0] > newrng[1]:
                    raise ValueError('lower edge of range is not <= upper')
                newrng = (radians(newrng[0]),radians(newrng[1]))
            self._range = newrng
            self._checkRange(self._decval)
        except ValueError:
            self._range = oldrange
            raise ValueError('Attempted to set range when value is out of range')
    def _getRange(self):
        if self._range is None:
            return None
        else:
            from math import degrees
            return degrees(self._range[0]),degrees(self._range[1])
    range=property(_getRange,_setRange,doc="""
    The acceptable range of angles for this :class:`AngularCoordinate` as a
    2-tuple (lower,upper) with both angles in degrees. Will raise a
    :exc:`ValueError` if the current value is outside the range.
    """)
    
    ############################################################################
    #                                                                          #
    #                                                                          #
    #  and then a monkey showed up                                             #
    #  and gave you a kiss                                                     #
    #  and you were confused                                                   #
    #                                                                          #
    #                                             comment poem by Rie O:-)     #
    ############################################################################
   
    def __str__(self):
        return self.getDmsStr(sep=('d',"'",'"'))
            
    def __eq__(self,other):
        if hasattr(other,'_decval'):
            return self._decval==other._decval
        else:
            return self._decval==other
        
    def __ne__(self,other):
        return not self.__eq__(other)
        
    def __add__(self,other):
        if hasattr(other,'_decval'):
            res = self.__class__()
            res._decval = self._decval + other._decval
        else:
            res = self.__class__()
            res._decval = self._decval + other
        return res
        
    def __sub__(self,other):
        if type(other) == AngularCoordinate:
            from math import degrees
            res = AngularSeperation()
            return AngularSeperation(degrees(other._decval),degrees(self._decval))
        else:
            res = AngularCoordinate()
            res._decval = self._decval - other
        return res
        
    def __mul__(self,other):
        res = self.__class__()
        res._decval = self._decval*other
        return res
        
    def __div__(self,other):
        res = self.__class__()
        res._decval = self._decval/other
        return res
        
    def __truediv__(self,other):
        res = self.__class__()
        res._decval = self._decval//other
        return res
        
    def __pow__(self,other):
        res = self.__class__()
        res._decval = self._decval**other
        return res
        
    def __float__(self):
        return self.degrees
        
    def getDmsStr(self,secform='%05.2f',sep=(unichr(176),"'",'"'), sign=True, canonical=False):
        """
        Generates the string representation of this AngularCoordinate as
        degrees, arcminutes, and arcseconds.
        
        :param secform: a formatter for the seconds
        :type secform: string
        :param sep:
            The seperator between components - defaults to degree sign, ' and "
            symbols.
        :type sep: string or 3-tuple of strings
        :param sign: Forces sign to be present before degree component.
        :type sign: boolean
        :param canonical: forces [+/-]dd:mm:ss.ss , overriding other arguments
        
        :returns: String representation of this object.
        """
        d,m,s = self.degminsec
        
        if canonical:
            sgn = '' if self._decval < 0 else '+'
            return '%s%02.i:%02.i:%05.2f'%(sgn,d,m,s)
        
        d,m=str(d),str(m)
        
        s = secform%s
        
        if isinstance(sep,basestring):
            if sep == 'dms':
                sep = ('d','m','s')
            sep = (sep,sep)
        
        tojoin = []
        
        if sign and self._decval  >= 0:
            tojoin.append('+')
        
        if d is not '0':
            tojoin.append(d)
            tojoin.append(sep[0])
                
        if m is not '0':
            tojoin.append(m)
            tojoin.append(sep[1])
                
        tojoin.append(s)
        if len(sep)>2:
            tojoin.append(sep[2])
            
        return ''.join(tojoin)
        
    def getHmsStr(self,secform = None,sep = ('h','m','s'), canonical = False):
        """
        gets the string representation of this AngularCoordinate as hours,
        minutes, and seconds
        
        secform is the formatter for the seconds component
        
        sep is the seperator between components - defaults to h, m, and s
        
        canonical forces [+/-]dd:mm:ss.ss , overriding other arguments
        
        Generates the string representation of this AngularCoordinate as hours,
        minutes, and seconds.
        
        :param secform: a formatter for the seconds component
        :type secform: string
        :param sep:
            The seperator between components - defaults to 'h', 'm', and 's'.
        :type sep: string or 3-tuple of strings
        :param canonical: forces [+/-]dd:mm:ss.ss , overriding other arguments
        
        :returns: String representation of this object.
        """
        
        h,m,s = self.hrsminsec
        
        if canonical:
            return '%02.i:%02.i:%06.3f'%(h,m,s)
        
        h,m=str(h),str(m)
        if secform is None:
            s = str(s)
        else:
            s = secform%s
        
        if isinstance(sep,basestring):
            if sep == 'hms':
                sep = ('h','m','s')
            sep = (sep,sep)
        
        tojoin = []
        
        tojoin.append(h)
        tojoin.append(sep[0])
            
        tojoin.append(m)
        tojoin.append(sep[1])
                
        tojoin.append(s)
        if len(sep)>2:
            tojoin.append(sep[2])
            
        return ''.join(tojoin)
    
def angular_string_to_dec(instr,hms=True,degrees=True):
    """
    Convinience function to convert a angular coordinate string to a decimal
    value.
    
    :param hms: 
        If True, the coordinate will be assumed to be h:m:s, otherwise d:m:s.
        This will be ignored if the coordinates are specified as ##h##m##s or
        ##d##m##s, or if the input is not in sexigesimal form.
    :type hms: boolean
    :param degrees: 
        If True, the output will be decimal degrees, otherwise radians.
    :type degrees: boolean
    
    :returns: Decimal value in radians or degrees
    """
    ac = AngularCoordinate(instr)
    if degrees:
        return ac.degrees
    else:
        return ac.radians

class AngularSeperation(AngularCoordinate):
    """
    This class represents a seperation between two angular coordinates on the
    unit sphere.
    
    A constructor is available, but the most natural way to generate this object
    is to use the subtraction (-) operator on two :class:`AngularCoordinate`
    objects or two :class:`LatLongCoordinates` objects.
    """
    
    def __init__(self,*args):
        """
        Input arguments can be either:
        
        * AngularSeperation(:class:`AngularSeperation` object) 
            Generates a copy of the provided object.
        * AngularSeperation(sep) 
            Generates a seperation of the provided distance with no starting point.
        * AngularSeperation(start,end) 
            Computes the seperation from the start and end objects, which must
            be :class:`AngularCoordinate` objects.
          
        """
        if len(args) == 1:
            a = args[0]
            if a.__class__ == self.__class__:
                self._decval = args[0]._decval
                self._range = args[0]._range
                return
            
            sep = a._decval if hasattr(a,'_decval') else a
        elif len(args) == 2:
            a0,a1 = args
            a0 = a0._decval if hasattr(a0,'_decval') else a0
            a1 = a1._decval if hasattr(a1,'_decval') else a1
            sep = a1 - a0
        else:
            raise ValueError('improper number of inputs to AngularSeperation')
        
        super(AngularSeperation,self).__init__(sep)
        
    def __add__(self,other):
        if isinstance(other,AngularCoordinate) and not self.__class__ == other.__class__:
            res = AngularCoordinate()
            res._decval = self._decval+other._decval
            return res
        else:
            return super(AngularSeperation,self).__add__(other)
        
    def _getArcsec(self):
        return self.degrees*3600
    def _setArcsec(self,val):
        self.degrees = val/3600
    arcsec = property(_getArcsec,_setArcsec,doc=None)
    
    def _getArcmin(self):
        return self.degrees*60
    def _setArcmin(self,val):
        self.degrees = val/60
    arcmin = property(_getArcmin,_setArcmin,doc=None)
    
        
    def projectedSeperation(self,zord,usez=False,**kwargs):
        """
        Computes the physical projected seperation assuming a given distance.
        
        kwargs are passed into :func:`cosmo_z_to_dist` if `usez` is True.
        
        :param zord: Redshift or distance
        :type zord: scalar number
        :param usez:
            If True, the input will be interpreted as a redshift, and kwargs
            will be passed into the distance calculation. The result will be in
            pc. Otherwise, `zord` will be interpreted as a distance.
        :type usez: boolean
        
        :returns: a float value for the seperation (in pc if redshift is used) 
        """
        return angular_to_physical_size(self.arcsec,zord,usez=usez,**kwargs)
    
    def seperation3d(self,zord1,zord2,usez=False,**kwargs):
        """
        computes the 3d seperation assuming the two points at the ends of this
        :class:`AngularSeperation` are at the distances `zord1` and `zord2`.  
        
        :param zord1: Redshift or distance for start point
        :type zord1: scalar number
        :param zord2: Redshift or distance for end point
        :type zord2: scalar number
        :param usez:
            If True, the inputs will be interpreted as a redshift, and kwargs
            will be passed into the distance calculation. The result will be in
            pc. Otherwise, `zord` will be interpreted as a distance.
        :type usez: boolean
        
        :returns: a float value for the seperation (in pc if redshift is used) 
        """
        from math import sin,cos,sqrt
        
        if usez:
            d1 = cosmo_z_to_dist(zord1,disttype=2,**kwargs)*1e6 #pc
            d2 = cosmo_z_to_dist(zord1,disttype=2,**kwargs)*1e6 #pc
        else:
            if len(kwargs)>0:
                raise TypeError('if not using redshift, kwargs should not be provided')
            d1 = zord1
            d2 = zord2
    
        costerm = 2*d1*d2*cos(self._decval)
        return sqrt(d1*d1+d2*d2-costerm)
    
#<-----------------------------Coordinate systems------------------------------>

class CoordinateSystem(object):
    """
    Base class of all coordinate systems.  Contains machinery for managing 
    conversion between coordinate systems. Subclasses must override
    :meth:`__init__`
    """
    from collections import defaultdict as _defaultdict
    
    __metaclass__ = ABCMeta
    __slots__ = tuple()
    
    @abstractmethod
    def __init__(self):
        raise NotImplementedError
    
    _converters = _defaultdict(dict) #first index is from, second is to
    
    @staticmethod
    def registerTransform(fromclass,toclass,func=None,overwrite=True):
        """
        Register a function to transform coordinates from one system to another.
        The transformation function is called is func(fromobject) and should 
        return a new object of type `toclass`.
        
        If the transformation function `func` is None, the function is taken to
        be a decorator, and one of `fromclass` or `toclass` may be the string
        'self' to indicate the function is a method (the class will be inferred
        from the class in which it is placed)
        
        :param fromclass: The class to transform from.
        :type fromclass: subclass of :class:`CoordinateSystem` or 'self'
        :param toclass: The class to transform to.
        :type toclass: subclass of :class:`CoordinateSystem` or 'self'
        :param func: the function to perform the transform or None if decorator.
        :type func: a callable or None
        :param overwrite: 
            If True, any already existing function will be silently overriden.
            Otherwise, a ValueError is raised.
        :type overwrite: boolean
        
        **Examples**::
        
            class MyCoordinates(CoordinateSystem):
                ...
            class YourCoordinates(CoordinateSystem):
                ...
            def transformer(mycooobj):
                ...
                return yourcoordobj
            CoordinateSystem.registerTransform(MyCoordinates,YourCoordinates,transformer)
            
            class TheirCoordinates(CoordinateSystem):
                @CoordinateSystem.registerTransform(MyCoordinates,'self')
                def fromMy(self,mycoordinates):
                    ...
                    return theircoordobj
        
        """
        if func is None:
            if fromclass != 'self':
                if not issubclass(fromclass,CoordinateSystem):
                    raise TypeError('from class for registerTransform must be a CoordinateSystem')
                
            if toclass != 'self':
                if not issubclass(toclass,CoordinateSystem):
                    raise TypeError('to class for registerTransform must be a CoordinateSystem')
            
            def innertrans(f):
                if fromclass == 'self':
                    fromclass = f.im_self.__class__
                    if not issubclass(fromclass,CoordinateSystem):
                        raise TypeError('from class for registerTransform must be a CoordinateSystem')
                    
                if toclass == 'self':
                    toclass = f.im_self.__class__
                    if not issubclass(fromclass,CoordinateSystem):
                        raise TypeError('to class for registerTransform must be a CoordinateSystem')
                    
                return CoordinateSystem.registerTransform(fromclass,toclass,f)
            
            return innertrans
        
        else:
            if not issubclass(fromclass,CoordinateSystem) or \
               not issubclass(toclass,CoordinateSystem):
               raise TypeError('to/from classes for registerTransform must be CoordinateSystems')
           
            if not overwrite and (toclass in CoordinateSystem._converters[fromclass]):
                raise ValueError('function already exists to convert {0} to {1}'.format(fromclass,toclass))
            
            CoordinateSystem._converters[fromclass][toclass] = func
        
    @staticmethod
    def getTransform(fromclass,toclass):
        """
        Returns the transformation function to go from `fromclass` to `toclass`.
        """
        return CoordinateSystem._converters[fromclass][toclass]
    
    @staticmethod
    def delTransform(fromclass,toclass):
        """
        Deletes the transformation function to go from `fromclass` to `toclass`.
        """
        del CoordinateSystem._converters[fromclass][toclass]
    
    def convert(self,tosys):
        """
        converts the coordinate system from it's current system to a new 
        :class:`CoordinateSystem` object.
        
        :param tosys: The new coordinate system 
        :type tosys: A subclass of :class:`CoordinateSystem`
        
        :except: raises NotImplementedError if conversion is not present
        """
        try:
            return CoordinateSystem._converters[self.__class__][tosys](self)
        except KeyError:
            strf = 'cannot convert coordinate system {0} to {1}'
            raise NotImplementedError(strf.format(self.__class__.__name__,tosys))
    

class RectangularCoordinates(CoordinateSystem):
    """
    Rectangular/Cartesian Coordinates in three dimensions. Coordinates are
    accessed via the attributes :attr:`x`, :attr:`y`, and :attr:`z`.
    """
    
    __slots__ = ('x','y','z')
    
    def __init__(self,x,y,z):
        self.x = x
        self.y = y
        #: description of z
        self.z = z
        
    def __getstate__(self):
        #TODO: watch if this creates probelms by not being a dict
        return dict(x=self.x,y=self.y,z=self.z)
    
    def __setstate__(self,d):
        self.x = d['x']
        self.y = d['y']
        self.z = d['z']
    
CartesianCoordinates = RectangularCoordinates

class RectangularEclipticCoordinates(RectangularCoordinates):
    """
    Rectangular coordinates oriented so that the x-y plane lies in the plane of
    the ecliptic at the specified epoch. Distances are in AU. Can be either
    geocentric or heliocentric.
    
    Note that the epoch cannot be set directly - if precession is desired
    desired, convert to some other coordinate system, set the epoch, and convert
    back.
    """
    __slots__ = ('_geo','_epoch')
    
    def __init__(self,x,y,z,geocentric,epoch=None):
        RectangularCoordinates.__init__(x,y,z)
        self.geocentric = geocentric
        self._epoch = epoch
        
    def _getGeocentric(self):
        return self._geo
    def _setGeocentric(self,val):
        self._geo = bool(val)
    geocentric = property(_getGeocentric,_setGeocentric,doc="""
    True if the coordinate system origin is the Earth 
    """)
    
    def _getHeliocentric(self):
        return not self._geo
    def _setHeliocentric(self,val):
        self._geo = not bool(val)
    heliocentric = property(_getHeliocentric,_setHeliocentric,doc="""
    True if the coordinate system origin is the Sun 
    """)
    
    @property
    def epoch(self):
        """
        Epoch of observation
        """
        return self._epoch
    
    
    

class _LatLongMeta(ABCMeta):
    def __init__(cls,name,bases,dct):
        super(_LatLongMeta,cls).__init__(name,bases,dct)
        if cls._latlongnames_[0] is not None:
            setattr(cls,cls._latlongnames_[0],cls.lat)
            setattr(cls,cls._latlongnames_[0]+'err',cls.laterr)
        if cls._latlongnames_[1] is not None:
            setattr(cls,cls._latlongnames_[1],cls.long)
            setattr(cls,cls._latlongnames_[1]+'err',cls.longerr)

class LatLongCoordinates(CoordinateSystem):
    """
    This object represents an angular location on a unit sphere as represented
    in spherical coordinates with a latitude and longitude.  Subclasses specify 
    details such as transformations or epochs.
    """
    __slots__ = ('_lat','_long','_laterr','_longerr')
    __metaclass__ = _LatLongMeta
    _latlongnames_ = (None,None)
    _longrange_ = None
    
    def __init__(self,lat=0,long=0,laterr=None,longerr=None):
        """
        See :attr:`lat` , :attr:`long` , :attr:`laterr` , and :attr:`longerr` 
        for the meaning of the inputs  
        """
        
        self._lat = AngularCoordinate(range=(-90,90))
        self._long = AngularCoordinate(range=self._longrange_)
        
        if hasattr(lat,'lat') and hasattr(lat,'long'):
            if long is 0 and laterr is None and longerr is None:
                self.lat = lat.lat
                self.long = lat.long
                self.laterr = lat.laterr
                self.longerr = lat.longerr
            else:
                raise ValueError("can't provide a LatLongCoordinates as a constructor and set other values simultaneously")
        else:
            self.lat = lat
            self.long = long
            self.laterr = laterr
            self.longerr = longerr
        
    def __getstate__(self):
        return dict([(k,getattr(k)) for k in LatLongCoordinates.__slots__])
    
    def __setstate__(self,d):
        for k in LatLongCoordinates.__slots__:
            setattr(k,d[k])
        
    def _getLat(self):
        return self._lat
    def _setLat(self,val):
        if isinstance(val,AngularCoordinate):
            rads = val.radians%_twopi
        else:
            rads = AngularCoordinate(val).radians%_twopi
        #fix for radian range
        if rads > 3*pi/2:
            rads -= _twopi
        elif rads > pi/2:
            rads = pi - rads
        self._lat.radians = rads
    lat = property(_getLat,_setLat,doc="""
    Latitude of this object as a :class:`AngularCoordinate` object.  May be set
    using any valid input form for :class:`AngularCoordinate`.
    """)
    
    def _getLong(self):
        return self._long
    def _setLong(self,val):
        if isinstance(val,AngularCoordinate):
            self._long.radians = val.radians%_twopi
        else:
            self._long.radians = AngularCoordinate(val).radians%_twopi
    long = property(_getLong,_setLong,doc="""
    Longitude of this object as a :class:`AngularCoordinate` object.  May be set
    using any valid input form for :class:`AngularCoordinate`.
    """)
    
    def _getLaterr(self):
        return self._laterr
    def _setLaterr(self,val):
        if val is None:
            self._laterr = None
        elif isinstance(val,AngularSeperation):
            self._laterr = val
        else:
            self._laterr = AngularSeperation(val)
    laterr = property(_getLaterr,_setLaterr,doc="""
    Latitude error for this object as a :class:`AngularSeperation` object. May
    be set using any valid input form for :class:`AngularSeperation`.
    """)
    
    def _getLongerr(self):
        return self._longerr
    def _setLongerr(self,val):
        if val is None:
            self._longerr = None
        elif isinstance(val,AngularSeperation):
            self._longerr = val
        else:
            self._longerr = AngularSeperation(val)
    longerr = property(_getLongerr,_setLongerr,doc="""
    Longitude error for this object as a :class:`AngularSeperation` object. May
    be set using any valid input form for :class:`AngularSeperation`.
    """)
    
    def __str__(self):
        lat,long = self._lat.d,self._long.d
        #lat,long = self._lat.getDmsStr(),self._long.getDmsStr()
        return '{0}: {1[0]}={2},{1[1]}={3}'.format(self.__class__.__name__,self._latlongnames_,lat,long)
    
    def getCoordinateString(self,sep=' ',labels=False,canonical=False,hmslong=False):
        coords = []
        if hmslong:
            coords.append(self._long.getHmsStr(canonical=canonical,sign=False))
        else:
            coords.append(self._long.getDmsStr(canonical=canonical,sign=False))
        coords[-1] = self._latlongnames_[1]+'='+coords[-1]
        coords.append(self._lat.getDmsStr(canonical=canonical))
        coords[-1] = self._latlongnames_[0]+'='+coords[-1]
        return sep.join(coords)
    
    def __eq__(self,other):
        if hasattr(other,'_lat') and hasattr(other,'_long'):
            return self._lat==other._lat and self._long==other._long
        else:
            return False
        
    def __ne__(self,other):
        return not self.__eq__(other)
    
    def __sub__(self,other):        
        if isinstance(other,self.__class__):
            from math import cos,degrees,acos,asin,sin
            
            b1 = self._lat.radians
            b2 = other._lat.radians
            db = abs(b2 - b1)
            dl = abs(other._long.radians - self._long.radians)
            
            #haversin(theta) = (1-cos(theta))/2 = sin^2(theta/2)
            #has better numerical accuracy if sin for theta ~ 0, cos ~ pi/2
            haversin = lambda t:(1-cos(t))/2 if pi/4 < (t%pi) < 3*pi/4 else sin(t/2)**2
            
            hdb = haversin(db)
            hdl = haversin(dl)
            
            havsep = hdb + cos(b1)*cos(b2)*hdl
            #archaversin
            sep = acos(1 - 2*havsep) if 0.25 < havsep <= 0.75 else 2*asin(havsep**0.5)
                
            #straightforward definition without the tweaks using haversin - this
            #is in principal faster, but in practice it ends up beeing about
            #10% faster due to the other overhead
            #sep = acos(sin(b1)*sin(b2)+cos(b1)*cos(b2)*cos(dl))
            
            return AngularSeperation(degrees(sep))
            
            #small angle version
#            dcorrlong = self._long.radians * cos(self._lat.radians) \
#                 - other._long.radians * cos(other._lat.radians)
#            dlat = self._lat.radians-other._lat.radians
#            sep = AngularSeperation(degrees((dlat*dlat+dcorrlong*dcorrlong)**0.5))
#            return sep
        else:
            raise ValueError("unsupported operand type(s) for -: '%s' and '%s'"%(self.__class__,other.__class__))
        
    def conversionMatrix(self,targetcoosys):
        """
        Generates and returns the transformation matrix from the current 
        coordinate system into the requested coordinate system
        
        :param targetcoosys: The target coordinate system
        :type targetcoosys: A subclass of :class:`LatLongCoordinates`
        
        :returns: a 3x3 transformation matrix, typically unitary/rotation matrix
        """
        from inspect import isclass
        
        if not isclass(targetcoosys) or not issubclass(targetcoosys,LatLongCoordinates):
            raise ValueError('can only generate conversion matrix for a valid coordinate system')
        
        if targetcoosys is self.__class__:
            return np.eye(3).view(np.matrix)
        
        raise NotImplementedError
        
    def transform(self,matrix,apply=True,unitarycheck=False):
        """
        Applies the supplied transformation matrix to these coordinates. The
        transform matrix is assumed to be unitary, although this is not checked
        unless `unitarycheck` is True.
        
        :param matrix: the transformation matrix in cartesian coordinates
        :type matrix: a 3x3 :class:`numpy.matrix`
        :param apply: 
            If True, the transform will be applied inplace to the coordinates
            for this object
        :type apply: boolean
        :param unitarycheck: 
            If True and the matrix is not unitary, a ValueError will be raised.
            Otherwise no check is performed.
        :type unitarycheck: boolean
        
        :returns: (lat,long) after the transformation matrix is applied
        """
        #for single values, math module is much faster than numpy 
        from math import sin,cos,atan2,sqrt
        
        m = np.asmatrix(matrix)
        
        if unitarycheck:
            mdagger = m.H
            rtol = 1e-5 if unitarycheck is True else unitarycheck
            if not np.allclose(mdagger*m,m*mdagger,rtol):
                raise ValueError('matrix not unitary')
        
        lat = self.lat.radians
        long = self.long.radians    
        
        #spherical w/ r=1 > cartesian
        x = cos(lat)*cos(long)
        y = cos(lat)*sin(long) 
        z = sin(lat)
        
        #do transform
        xp,yp,zp = m*np.matrix((x,y,z))
        
        #cartesian > spherical
        latp = atan2(zp,sqrt(xp*xp+yp*yp))
        longp = atan2(yp,xp)
        
        if apply:
            self.lat = latp
            self.long = longp
        
        return latp,longp

class HorizontalCoordinates(LatLongCoordinates):
    """
    This object represents an angular location on the unit sphere, with the 
    north pole of the coordinate position fixed to the local zenith
    
    To convert from other :class:`Coordinate` types to horizontal positions, see 
    :class:`astropysics.obstools.Site`, as site information is required for
    these corrections
    """  
    __slots__ = tuple()
    _latlongnames_ = ('alt','az')
    _longrange_ = (0,360)
    
class EpochalCoordinates(LatLongCoordinates):
    """
    The origin and orientation of some coordinate systems are tied to the motion
    of the Earth. Hence, a particular location of the equinox as specified by
    the epoch.
    
    Subclasses must implement the :meth:`transformToEpoch` method.
    """
    __slots__ = ('_epoch')
    
    #: If True, this coordinate system uses Julian Epochs.  Otherwise, Besselian
    julianepoch = True 
    
    def __init__(self,lat=0,long=0,laterr=None,longerr=None,epoch=None):
        LatLongCoordinates.__init__(self,lat,long,laterr,longerr)
        self._epoch = epoch
        
    
    def __getstate__(self):
        d = LatLongCoordinates.__getstate__(self)
        d['_epoch'] = self._epoch
        return d
    
    def __setstate__(self,d):
        LatLongCoordinates.__setstate__(self,d)
        self._epoch = d['_epoch']
    
    def _getEpoch(self):
        return self._epoch
    def _setEpoch(self,val):
        if val is None:
            self._epoch = None
        elif not hasattr(self,'_epoch') or self._epoch is None:
            self._epoch = float(val)
        else:
            self.transformToEpoch(float(val))
    epoch = property(_getEpoch,_setEpoch,doc="""
    Epoch for this coordinate. If set, this coordinate will be transformed to
    the new epoch.
    """)
    
    def _getEpochstr(self):
        return '{0}{1}'.format('J' if self.julianepoch else 'B',self._epoch)
    def _setEpochstr(self,val):
        self.epoch = val
    epochstr = property(_getEpochstr,_setEpochstr,doc="""
    A string representation of the current Epoch with a J or B prefixed for
    julian or besselian epochs.
    """)
    
    def _getJdepoch(self):
        from .obstools import epoch_to_jd
        return epoch_to_jd(self._epoch,self.julianepoch)
    def _setJdepoch(self,val):
        from .obstools import jd_to_epoch
        self._epoch = jd_to_epoch(val,self.julianepoch)
    jdepoch = property(_getJdepoch,_setJdepoch,doc="""
    Julian Date of the current epoch.  If set, it is assumed to be a Julian
    Epoch.
    """)
    
    @abstractmethod
    def transformToEpoch(self,newepoch):
        raise NotImplementedError
    

        

class EquatorialCoordinatesBase(EpochalCoordinates):
    """
    This object represents an angular location on the unit sphere, specified in
    right ascension and declination.  Some of the subclasses are not strictly 
    speaking equatorial, but they are close, or are tied to the equatorial 
    position of a particular epoch.
    
    This is a superclass for all other Equatorial Coordinate systems - particular
    reference systems implement the :meth:`transformToEpoch` method.
    """
    
    __slots__ = tuple()
    _latlongnames_ = ('dec','ra')
    _longrange_ = (0,360)
    
        
    def __str__(self):
        rastr = self.ra.getHmsStr(canonical=True)
        decstr = self.dec.getDmsStr(canonical=True)
        return 'Equatorial Coordinates: {0} {1} ({2})'.format(rastr,decstr,self.epoch)
    
    def __init__(self,*args,**kwargs):
        """
        input may be in the following forms:
        
        * EquatorialCoordinates()
        * EquatorialCoordinates(EquatorialCoordinates)
        * EquatorialCoordinates('rastr decstr')
        * EquatorialCoordinates(ra,dec)
        * EquatorialCoordinates(ra,dec,raerr,decerr)
        * EquatorialCoordinates(ra,dec,raerr,decerr,epoch)
        
        """
        posargs = {}
        if len(args) == 0:
            pass
        if len(args) == 1:
            if isinstance(args[0],EquatorialCoordinates):
                super(EquatorialCoordinates,self).__init__(args[0])
                self.epoch = args[0].epoch
                return
            elif isinstance(args[0],basestring):
                sargs = args[0].split()
                posargs['ra'] = sargs[0]
                posargs['dec'] = sargs[1]
        elif len(args) == 2:
            posargs['ra'] = args[0]
            posargs['dec'] = args[1]
        elif len(args) == 4:
            posargs['ra'] = args[0]
            posargs['dec'] = args[1]
            posargs['raerr'] = args[2]
            posargs['decerr'] = args[3]
        elif len(args) == 5:
            posargs['ra'] = args[0]
            posargs['dec'] = args[1]
            posargs['raerr'] = args[2]
            posargs['decerr'] = args[3]
            posargs['epoch'] = args[4]
        
        for k,v in posargs.iteritems():
            if k in kwargs:
                raise ValueError('got multiple values for argument '+k)
            kwargs[k] = v
        
        kwargs.setdefault('ra',0)
        kwargs.setdefault('dec',0)
        kwargs.setdefault('raerr',None)
        kwargs.setdefault('decerr',None)
        kwargs.setdefault('epoch',2000)
        
        super(EquatorialCoordinatesBase,self).__init__(kwargs['dec'],kwargs['ra'],kwargs['decerr'],kwargs['raerr'])
        if 'epoch' in kwargs:
            self.epoch = kwargs['epoch']
            
class EquatorialCoordinatesEquinox(EquatorialCoordinatesBase):
    """
    TODO: document, clean up
    """
    
    def transformToEpoch(self,newepoch):
        """
        Transforms these :class:`EquatorialCoordinates` to a new epoch using the
        IAU 2000 precessions from Capitaine, N. et al. 2003.
        """
        #convert from current to J2000
        B = self._precessionMatrixJ2000(self.epoch).I
        #convert to new epoch
        A = self._precessionMatrixJ2000(newepoch)
        self.transform(A*B)
    
    @staticmethod
    def _precessionMatrixJ2000(epoch):
        """
        computes the precession matrix from J2000 to the given Julian Epoch
        """
        T = (epoch-2000.0)/100.0
#        pzeta = (-0.0000002,-0.0000327,0.0179663,0.3019015,2306.0809506,2.5976176)
#        pz = (-0.0000003,0.0000470,0.0182273,1.0947790,2306.0803226,-2.5976176)
#        ptheta = (-0.0000001,-0.0000601,-0.0418251,-0.4269353,2004.1917476,0.0)
        #from USNO circular
        pzeta = (-0.0000003173,-0.000005971,0.01801828,0.2988499,2306.083227,2.650545)
        pz = (-0.0000002904,-0.000028596,0.01826837,1.0927348,2306.077181,-2.650545)
        ptheta = (-0.0000001274,-0.000007089,-0.04182264,-0.4294934,2004.191903,0)
        zeta = np.polyval(pzeta,T)/3600.0
        z = np.polyval(pz,T)/3600.0
        theta = np.polyval(theta,T)/3600.0
        
        return rotation_matrix(-z,'z') *\
               rotation_matrix(theta,'y') *\
               rotation_matrix(-zeta,'z')
            
    @property
    def refsys(self):
        return None
    
class EquatorialCoordinatesCIO(EquatorialCoordinatesBase):
    """
    TODO: implement
    """
    
    def __init__(self):
        raise NotImplementedError
            
            
class EquatorialCoordinatesICRS(EquatorialCoordinatesBase):
    """
    Equatorial Coordinates tied to the International Celestial Reference System
    (ICRS).  Strictly speaking this is not an Equatorial system, as it is an
    inertial frame that only aligns with Earth's equator at J2000, but it is
    conventional to treat it as such, but independent of Epoch.
    """
    def transformToEpoch(self,newepoch):
        """
        ICRS is an inertial frame, so no transformation is necessary
        """
        pass
    
    @property
    def refsys(self):
        return 'ICRS'
    
class EquatorialCoordinatesFK5(EquatorialCoordinatesEquinox):
    """
    Equatorial Coordinates fixed to the FK5 reference system. 
    """
    
    def transformToEpoch(self,newepoch):
        """
        Transforms these :class:`EquatorialCoordinates` to a new epoch. Uses the 
        algorithm resolved by the IAU in 1976 as written in Meeus and 
        Lieske,J.H. 1979
        """
        self.transform(self._precessionMatrixJ(self.epoch,newepoch))
    
    @staticmethod
    def _precessionMatrixJ(epoch1,epoch2):
        """
        computes the precession matrix from one Julian epoch to another
        """
        from .obstools import epoch_to_jd
        
        jd1 = epoch_to_jd(epoch1)
        jd2 = epoch_to_jd(epoch2)
        
        T = (jd1 - 2451545.0)/36525
        dt = (jd2 - jd1)/36525
        
        pzeta = (0.017998,0.000344,0.30188,-0.000139,1.39656,2306.2181)
        temp = pzeta[5] + T*(pzeta[4]+T*pzeta[3])
        zeta = dt*(temp + dt*((pzeta[2]+pzeta[1]*T) + dt*pzeta[0]))/3600
        
        pz = (0.018203,-0.000066,1.09468)
        z = t*(temp + dt*((pz[2]+pz[1]*T) + dt*pz[0]))/3600
        
        ptheta = (-0.041833,-0.000217,-0.42665,-0.000217,-0.85330,2004.3109)
        temp = ptheta[5] + T*(ptheta[4]+T*ptheta[3])
        zeta = dt*(temp + dt*((ptheta[2]+ptheta[1]*T) + dt*ptheta[0]))/3600
        
        return rotation_matrix(-z,'z') *\
               rotation_matrix(theta,'y') *\
               rotation_matrix(-zeta,'z')
    
    @property
    def refsys(self):
        return 'FK5'
    
class EquatorialCoordinatesFK4(EquatorialCoordinatesEquinox):
    """
    Equatorial Coordinates fixed to the FK4 reference system.  Note that this 
    implementation does *not* correct for the elliptic terms of aberration
    as of yet.
    
    Epoch is Besselian.
    """
    
    julianepoch = False
    
    def transformToEpoch(self,newepoch):
        """
        Transforms these :class:`EquatorialCoordinates` to a new epoch. Uses the
        method of Newcomb (pre-IAU1976) to compute precession.
        """
        self.transform(self._precessionMatrixB(self.epoch,newepoch))
    
    @staticmethod
    def _precessionMatrixB(epoch1,epoch2):
        """
        computes the precession matrix from one Besselian epoch to another using
        Newcomb's method.
        """
        #tropical years
        t1 = (epoch1-1850.0)/1000.0    
        t2 = (epoch2-1850.0)/1000.0
        dt = t2 - t1
        
        zeta1 = 23035.545 + t1*139.720+0.060*t1*t1
        zeta2 = 30.240 - 0.27*t1
        zeta3 = 17.995
        pzeta = (zeta3,zeta2,zeta1,0)
        zeta = np.polyval(pzeta,dt)
        
        z1 = 23035.545 + t1*139.720 + 0.060*t1*t1
        z2 = 109.480 + 0.39*t1
        z3 = 18.325
        pz = (z3,z2,z1,0)
        z = np.polyval(pz,dt)
        
        theta1 = 20051.12 - 85.29*t1 - 0.37*t1*t1
        theta2 = -42.65 - 0.37*t1
        theta3 = -41.8
        ptheta = (theta3,theta2,theta1,0)
        theta = np.polyval(ptheta,dt)
        
        return rotation_matrix(-z,'z') *\
               rotation_matrix(theta,'y') *\
               rotation_matrix(-zeta,'z')
    
    @property
    def refsys(self):
        return 'FK4'
    
    
#Default Equatorial Coordinate system is J2000 equinox... 
#TODO:change default to CIO when CIO is ready
EquatorialCoordinates = EquatorialCoordinatesEquinox
    
class EclipticCoordinates(EpochalCoordinates):
    """
    Ecliptic Coordinates (beta, lambda) such that the fundamental plane passes
    through the ecliptic at the equinox for the specified epoch.
    
    This particular implementation is tied to
    :class:`EquatorialCoordinatesDynamical2000` for epoch transforms.
    """
    
    __slots__ = tuple()
    _latlongnames_ = ('beta','lamb')
    _longrange_ = (0,360)
    
    def __init__(self,beta=0,lamb=0,betaerr=None,lamberr=None,epoch=2000):
        EpochalCoordinates(beta,lamb,betaerr,lamberr,epoch)
        
    def transformToEpoch(self,newepoch):
        eqc = self.convert(EquatorialCoordinatesDynamical2000)
        eqc.epoch = newepoch
        newval = eqc.convert(self.__class__)
        self._lat._decval = newval._lat._decval
        self._long._decval = newval._long._decval
        self._laterr._decval = newval._lat._decval
        self._longerr._decval = newval._longerr._decval
        self._epoch = newepoch
    
    @property
    def refsys(self):
        return None
        
    
class GalacticCoordinates(LatLongCoordinates):
    __slots__ = tuple()
    _latlongnames_ = ('b','l')
    _longrange_ = (0,360)
    
    _ngp_J2000 = EquatorialCoordinatesFK5(192.859508, 27.128336,epoch=2000)
    _long0_J2000 = AngularCoordinate(122.932)
    
    def toSGal(self):
        """
        converts this position to Supergalactic coordinates
        """
        latang = SupergalacticCoordinates._nsgp_gal.lat.d
        longang = SupergalacticCoordinates._nsgp_gal.long.d
        mrot = rotation_matrix(90-latang,'x')*rotation_matrix(90+longang,'z')
        sgp = SupergalacticCoordinates(self)
        sgp.transform(mrot)
        return sgp
    
    
class SupergalacticCoordinates(LatLongCoordinates):   
    __slots__ = tuple()
    _latlongnames_ = ('sgb','sgl')
    _longrange_ = (0,360)
    
    _nsgp_gal = EquatorialCoordinatesFK4(6.32,47.37,epoch=1950)
    _sglong0_gal = 137.37
    _nsgp_J2000 = EquatorialCoordinatesFK5(283.75420420,15.70894043,epoch=2000)
    _sglong0_J2000 = 42.30997710
    

def objects_to_coordinate_arrays(posobjs,coords='auto',degrees=True):
    """
    converts a sequence of position objects into an array of coordinates.  
    
    `coords` determines the order of the output coordinates - it can be a 
    comma-seperated list of coordinate names or if 'auto', it will be 'lat,long'
    for all coordinate systems except for Equatorial, which will use 'ra,dec'
    
    if `degrees` is True, returned arrays are in degrees, otherwise radians
    """
    if coords=='auto':
        coordnames = None
    else:
        coordnames = coords.split(',')
        
    coords = []
    if degrees:
        for o in posobjs:
            if coordnames is None:
                if isinstance(o,EquatorialCoordinates):
                    coords.append((o.ra.d,o.dec.d))
                else:
                    coords.append((o.lat.d,o.long.d))
            else:
                coords.append([getattr(o,c).d for c in coordnames])
    else:
        for o in posobjs:
            if coordnames is None:
                if isinstance(o,EquatorialCoordinates):
                    coords.append((o.ra.r,o.dec.r))
                else:
                    coords.append((o.lat.r,o.long.r))
            else:
                coords.append([getattr(o,c).r for c in coordnames])

    return np.array(coords).T

def rotation_matrix(angle,axis='z',degrees=True):
    """
    generates a 3x3 rotation matrix in cartesian coordinates for rotation about
    the requested axis.
    
    `axis` can either be a string 'x','y', or 'z', or a 3-sequence specifying
    an axis to rotate about.
    
    if `degrees` is True the input angle is in degrees, otherwise it is radians
    """
    from math import sin,cos,radians,sqrt
    if degrees:
        angle = radians(angle)
        
    
    
    if axis == 'z':
        s = sin(angle)
        c = cos(angle)
        return np.matrix((( c,-s, 0),
                          ( s, c, 0),
                          ( 0, 0, 1)))
    elif axis == 'y':
        s = sin(angle)
        c = cos(angle)
        return np.matrix((( c, 0,-s),
                          ( 0, 1, 0),
                          ( s, 0, c)))
    elif axis == 'x':
        s = sin(angle)
        c = cos(angle)
        return np.matrix((( 1, 0, 0),
                          ( 0, c,-s),
                          ( 0, s, c)))
    else:
        x,y,z = axis
        w = cos(angle/2)
        
        #normalize
        if w == 1:
            x=y=z=0
        else:
            l = sqrt((x*x + y*y + z*z)/(1-w*w))
            x /= l
            y /= l
            z /= l
        
        wsq = w*w
        xsq = x*x
        ysq = y*y
        zsq = z*z
        return np.matrix((( wsq+xsq-ysq-zsq, 2*x*y-2*w*z, 2*x*z+2*w*y),
                          ( 2*x*y+2*w*z, wsq-xsq+ysq-zsq,2*y*z-2*w*x),
                          ( 2*x*z-2*w*y, 2*y*z+2*w*x, wsq-xsq-ysq+zsq)))
def angle_axis(matrix,degrees=True):
    """
    Computes the angle of rotation and the rotation axis for a given rotation
    matrix.
    
    :param matrix: the rotation matrix
    :type matrix: a 3x3 :class:`numpy.ndarray`
    :param degrees: if True, output is in degrees
    :type degrees: boolean
    
    :returns:
        an (angle,axis) tuple where the angle is in degrees if `degrees` is
        True, otherwise in radians
        
    """
    from math import sin,cos,acos,degrees,sqrt
    
    m = np.asmatrix(matrix)
    if m.shape != (3,3):
        raise ValueError('matrix is not 3x3')
    
    
    
    angle = acos((m[0,0] + m[1,1] + m[2,2] - 1)/2)
    denom = sqrt(2*((m[2,1]-m[1,2])+(m[0,2]-m[2,0])+(m[1,0]-m[0,1])))
    axis = np.array((m[2,1]-m[1,2],m[0,2]-m[2,0],m[1,0]-m[0,1]))/denom
    axis /= sqrt(np.sum(axis**2)) 
    
    if degrees:
        return degrees(angle),axis
    else:
        return angle,axis
    
def obliquity(jd,algorithm=2000):
    """
    Computes the obliquity of the Earth at the requested Julian Date.  
    
    :param jd: julian date at which to compute obliquity
    :type jd: scalar or array-like
    :param algorithm: year of IAU algorithm - can be 2000 (default) or 1980
    :type algorithm: int
    
    :returns: mean obliquity in degrees (or array of obliquities)
    """
    T = (jd-2451545.0)/36525.0
    
    if algorithm==2000:
        p = (-0.0000000434,-0.000000576,0.00200340,-0.0001831,-46.836769,84381.406)
    elif algorithm==1980:
        p = (0.001813,-0.00059,-46.8150,84381.448)
    else:
        raise ValueError('invalid algorithm year for computing obliquity')
        
    return np.polyval(p,T)/3600.
    
    
#<--------------------------- Ephemerides classes ----------------------------->
class EphemerisAccuracyWarning(Warning):
    """
    Class for warnings due to Ephemeris accuracy issues
    """
    
class EphemerisObject(object):
    """
    An object that can be used to generate positions on the sky for a given 
    date and time as dictated by the :attr:`jd` attribute.
    
    :meth:`equatorialCoordinates` must be overridden.
    """
    
    __metaclass__ = ABCMeta
    
    name = '' #put here so it ends up in autogenerated documentation
    jd2000 = 2451545.0 #set default epoch to J2000.0
    
    def __init__(self,name,jd0=None,validjdrange=None):
        self.name = name
        self.jd0 = EphemerisObject.jd2000 if jd0 is None else jd0
        self._jd = self._jd0
        self.validjdrange = validjdrange
    
    def _getJd0(self):
        return self._jd0
    def _setJd0(self,val):
        from operator import isSequenceType
        from .obstools import calendar_to_jd
        from datetime import datetime
        
        if hasattr(val,'year') or isSequenceType(val):
            self._jd0 = calendar_to_jd(val)
        else:
            self._jd0 = val
    jd0 = property(_getJd0,_setJd0,doc="""
    The Epoch for this object - when :attr:`jd` equals this value, :attr:`d` is
    0. Can be set as a decimal number, :class:`datetime.datetime` object, or a
    gregorian date tuple.
    """)
    
    
    def _getJd(self):
        return self._jd
    def _setJd(self,val):
        from operator import isSequenceType
        from .obstools import calendar_to_jd
        from datetime import datetime
        
        if val == 'now':
            jd =  calendar_to_jd(datetime.utcnow(),tz=None)
        elif hasattr(val,'year') or isSequenceType(val):
            jd = calendar_to_jd(val)
        else:
            jd = val
        if self._validrange is not None:
            from warnings import warn
            if jd < self._validrange[0]:
                warn('JD {0} is below the valid range for this EphemerisObject'.format(jd),EphemerisAccuracyWarning)
            elif jd > self._validrange[1]:
                warn('JD {0} is above the valid range for this EphemerisObject'.format(jd),EphemerisAccuracyWarning)
        self._jd = jd
        
    jd = property(_getJd,_setJd,doc="""
    Julian Date at which to calculate the orbital elements. Can be set either as
    a scalar JD, 'now', :class:`datetime.datetime` object or a compatible tuple.
    """)
    
    def _getD(self):
        return self._jd - self._jd0
    def _setD(self,val):
        self._jd = val + self._jd0
    d = property(_getD,_setD,doc='the julian date offset by the epoch')
    
    def _getValidjdrange(self):
        if self._validrange is None:
            return (None,None)
        else:
            return self._validrange
    def _setValidjdrange(self,val):
        if val is None:
            self._validrange = None
        else:
            v1,v2 = val
            if v1 is None and v2 is None:
                self._validrange = None
            else:
                from operator import isSequenceType
                from .obstools import calendar_to_jd
                from datetime import datetime
                
                vs = []
                for v in (v1,v2):
                    if v is None:
                        vs.append(None)
                    elif v == 'now':
                        vs.append(calendar_to_jd(datetime.utcnow(),tz=None))
                    elif hasattr(val,'year') or isSequenceType(val):
                        vs.append(calendar_to_jd(val))
                    else:
                        vs.append(val)
                self._validrange = tuple(vs)
    validjdrange = property(_getValidjdrange,_setValidjdrange,doc="""
    The range of jds over which these Ephemerides are valid. Should be a 2-tuple
    set as the :attr:`jd` attribute indicating (minjd,maxjd). Either can be None
    to indicate no bound.  If set to None, the result will be (None,None)
    """)
    
    @abstractmethod    
    def equatorialCoordinates(self):
        """
        Returns the equatorial coordinates of this object at the current
        date/time as a :class:`EquatorialCoordinates` object.
        
        Must be overridden in subclasses.
        """
        raise NotImplementedError
    
    def radecs(self,ds,usejd=False):
        """
        Generates an array of RAs and Decs for a set of input julian dates. `ds`
        must be a sequence of objects that can be set to `d` or `jd`.
        
        If `usejd` is True, the inputs are interpreted as Julian Dates without
        the epoch offset. Otherwise, they are interpreted as offsets from `jd0`.
        
        Returns a 2xN array with the first column RA and the second Dec in
        degrees.
        """
        
        oldjd = self._jd
        try:
            ra = []
            dec = []
            for d in ds:
                if usejd:
                    self.jd = d
                else:
                    self.d = d
                    
                eqpos = self.equatorialCoordinates()
                ra.append(eqpos.ra.d)
                dec.append(eqpos.dec.d)
                
            return np.array((ra,dec))
        finally:
            self._jd = oldjd
            
class SolarSystemObject(EphemerisObject):
    """
    A :class:`EphemerisObject` that can be interpreted as an object in the Solar
    System.  
    
    :meth:`cartesianCoordinates` must be overridden in subclasses.
    """
    
    def _obliquity(self,jd):
        """
        obliquity of the Earth/angle of the ecliptic in degrees
        
        the input `jd` is the actual Julian Day, *not* the offset `d` used for
        the orbital elements
        """
        #TODO: eventually pull this from Ecliptic coordinate transform
        return 23.4393 - 3.563E-7 * (jd - KeplerianOrbit.jd2000)
    
    @abstractmethod
    def cartesianCoordinates(self,geocentric=False):
        """
        Returns the ecliptic rectangular coordinates of this object
        at the current date/time as an (x,y,z) tuple (in AU).
        
        If `geocentric` is True, return geocentric coordinates.  Otherwise, 
        heliocentric.
        """
        raise NotImplementedError
    
    def equatorialCoordinates(self):
        """
        Returns the equatorial coordinates of this object at the current
        date/time as a :class:`EquatorialCoordinates` object for the epoch at which
        they are derived.
        """
        from math import radians,degrees,cos,sin,atan2,sqrt
        from .obstools import jd_to_epoch
        
        if hasattr(self,'_eqcache') and self._eqcache[0] == self._jd:
            return EquatorialCoordinates(*self._eqcache[1:],epoch=jd_to_epoch(self._jd))
        
        jd = self.jd
        
        eclr = radians(self._obliquity(jd))
        
        #heliocentric coordinates
        xh,yh,zh = self.cartesianCoordinates()
        
        #get Earth position - from the Sun ephemeris
        xs,ys,zs = _earth_coords(jd)
        
        #switch to geocentric coordinates
        xg = xh - xs
        yg = yh - ys
        zg = zh - zs
        
        #finally correct for obliquity to get equatorial coordinates
        cecl = cos(eclr)
        secl = sin(eclr)
        x = xg
        y = cecl*yg - secl*zg
        z = secl*yg + cecl*zg
        
        ra = degrees(atan2(y,x))
        dec = degrees(atan2(z,sqrt(x*x+y*y)))
        
        #cache for faster retrieval if JD is not changed
        self._eqcache = (self._jd,ra,dec)
        return EquatorialCoordinates(ra,dec,epoch=jd_to_epoch(self._jd))
    
    def phase(self,perc=False):
        """
        Compute the phase of this object - 0 is "new", 1 is "full".
        
        if `perc` is True, returns percent illumination.
        """
        from math import sqrt
        
        xh,yh,zh = self.cartesianCoordinates()
        
        xs,ys,zs = _earth_coords(jd)
        
        xg = xh - xs
        yg = yh - ys
        zg = zh - zs
        
        r = sqrt(xh*xh+yh*yh+zh*zh)
        R = sqrt(xg*xg+yg*yg+zg*zg)
        s = sqrt(xs*xs+ys*ys+zs*zs)
        
        phase = (1+(r*r + R*R - s*s)/(2*r*R))/2
        
        if perc:
            return 100*phase
        else:
            return phase
    
class KeplerianOrbit(SolarSystemObject):
    """
    An object with orbital elements (probably a solar system body) that can be
    used to construct ephemerides.
    
    The orbital elements are accessible as properties, computed for a Julian
    Date given by the :attr:`jd` attribute. They can also be set to a function
    of the form `element(d)`, where `d` is the offset from `jd0`. Alternatively,
    subclasses may directly override the orbital elements with their own custom
    properties that should return orbital elements at time `d`. The primary
    orbital elements are:
    
    * :attr:`e`
        ellipticity 
    * :attr:`a`
        semimajor axis (AU)
    * :attr:`i` 
        is the orbital inclination (degrees)
    * :attr:`N` 
        is the longitude of the ascending node (degrees)
    * :attr:`w` 
        is the argument of the perihelion (degrees)
    * :attr:`M`
        is the mean anamoly (degrees)
    
    Note that the default algorithms used here (based on heavily modified
    versions of `these methods <http://stjarnhimlen.se/comp/ppcomp.html>`_) are
    only accurate to ~ 1 arcmin within a millenium or so of J2000, but are
    computationally quite fast and simple.
    """
    
    def __init__(self,name,e,a,i,N,w,M,jd0=None,jdnow=None):
        """
        Generates an object with orbital elements given a generator 
        
        Arguments for these orbital elements can be either fixed values or
        functions of the form f(jd-jd0) that return the orbital element as a
        function of Julian Day from the epoch
        
        `name` is a string describing the object `jd0` is the epoch for these
        orbital elements (e.g. where their input functions are 0). To use raw
        JD, set this to 0. If None, it defaults to J2000
        
        `jdnow` can be used to set the initial JD.  If None, it will be the same
        as `jd0`
        """
        if jd0 is None:
            jd0 = EphemerisObject.jd2000 - 0.5
        EphemerisObject.__init__(self,name,jd0)
        
        self.e = e
        self.a = a
        self.i = i
        self.N = N
        self.w = w
        self.M = M
        self.name = name
        
        self.jd0 = jd0
        self._jd = jd0
        if jdnow is None:
            self._jd = jd0
        else:
            self.jd = jdnow
        
    
    #primary orbital elements
    def _getE(self):
        return self._e(self.d)
    def _setE(self,val):
        if callable(val):
            self._e = val
        else:
            self._e = lambda d:val
    e = property(_getE,_setE,doc='orbital eccentricity')
    
    def _getA(self):
        return self._a(self.d)
    def _setA(self,val):
        if callable(val):
            self._a = val
        else:
            self._a = lambda d:val
    a = property(_getA,_setA,doc='semi-major axis (au)')
    
    def _getI(self):
        return self._i(self.d)
    def _setI(self,val):
        if callable(val):
            self._i = val
        else:
            self._i = lambda d:val
    i = property(_getI,_setI,doc='inclination (degrees)')
    
    def _getN(self):
        return self._N(self.d)
    def _setN(self,val):
        if callable(val):
            self._N = val
        else:
            self._N = lambda d:val
    N = property(_getN,_setN,doc='Longitude of the ascending node (degrees)')
    
    def _getW(self):
        return self._w(self.d)
    def _setW(self,val):
        if callable(val):
            self._w = val
        else:
            self._w = lambda d:val
    w = property(_getW,_setW,doc='Argument of the perihelion (degrees)')
    
    def _getM0(self):
        return self._M0(self.d)
    def _setM0(self,val):
        if callable(val):
            self._M0 = val
        else:
            self._e = lambda d:val
    M0 = property(_getM0,_setM0,doc='Mean anamoly (degrees)')
    
    #secondary/read-only orbital elements
    
    @property
    def lw(self):
        """
        longitude of the perihelion (degrees): :math:`N + w`
        """
        return self.N + self.w
    
    @property
    def L(self):
        """
        mean longitude: (degrees):math:`M + lw`
        """
        return self.M + self.N + self.w
    
    @property
    def dperi(self):
        """
        distance at perihelion (AU): :math:`a(1-e)`
        """
        return self.a*(1 - self.e)
    
    @property
    def dapo(self):
        """
        distance at apohelion (AU): :math:`a(1+e)`
        """
        return self.a*(1 + self.e)
    
    @property
    def P(self):
        """
        orbital period (years): :math:`a^{3/2}`
        """
        return self.a**1.5
    
    @property
    def T(self):
        """
        time of perihelion (in *offset* JD i.e. `d`)
        """
        return - self.M/(self.P*360.0)
    
    @property
    def Eapprox(self):
        """
        *approximate* Eccentric anamoly - faster than proper numerical solution
        of the E-M relation, but lower precision
        """
        from math import radians,sin,cos,degrees
        Mr = radians(self.M)
        e = self.e
        return degrees(Mr + e*sin(Mr)*(1.0 + e*cos(Mr)))
            
    @property
    def vapprox(self):
        """
        *approximate* Eccentric anamoly - faster than proper numerical solution
        of the E-M relation, but lower precision
        """
        from math import radians,sin,cos,atan2,sqrt,degrees
        
        Mr = radians(self.M)
        e = self.e
        
        E = Mr + e*sin(Mr)*(1.0 + e*cos(Mr))
        xv = cos(E) - e
        yv = sqrt(1.0 - e*e) * sin(E)
        
        return degrees(atan2(yv,xv))
    
    def cartesianCoordinates(self,geocentric=False):
        """
        Returns the heliocentric ecliptic rectangular coordinates of this object
        at the current date/time as an (x,y,z) tuple (in AU)
        """
        from math import radians,degrees,cos,sin,atan2,sqrt
        
        #now get the necessary elements
        Mr = radians(self.M)
        wr = radians(self.w)
        ir = radians(self.i)
        Nr = radians(self.N)
        e = self.e
        a = self.a
        
        #compute coordinates
        #approximate eccentric anamoly
        E = Mr + e*sin(Mr)*(1.0 + e*cos(Mr))
        
        xv = a*(cos(E) - e)
        yv = a*(sqrt(1.0 - e*e) * sin(E))
        
        v = atan2(yv,xv)
        r = sqrt(xv*xv + yv*yv)
        
        sN = sin(Nr)
        cN = cos(Nr)
        si = sin(ir)
        ci = cos(ir)
        svw = sin(v + wr)
        cvw = cos(v + wr)
        
        #convert to heliocentric ecliptic coords
        xh = r*(cN*cvw - sN*svw*ci)
        yh = r*(sN*cvw + cN*svw*ci)
        zh = r*(svw*si)
        
        if geocentric:
            xg,yg,zg = _earth_coords(self._jd)
            return xh+xg,yh+yg,zh+zg
        else:
            return xh,yh,zh
    
    
class Sun(KeplerianOrbit):
    """
    This class represents the Sun's ephemeris.  Properly this is actually the 
    Earth's ephemeris, but it's still the way to get the on-sky location of the 
    sun
    """
    
    _validrange = (2415021.0,2488070.0)
    
    def __init__(self,jdordate=None):    
        """
        Initialize the object and optionally set the initial date with the 
        `jdordate` argument (by default this is J2000)
        """
        EphemerisObject.__init__(self,name='Sol',jd0=KeplerianOrbit.jd2000-0.5)
            
        if jdordate is None:
            self.jd = self.jd0 
        else:
            self.jd = jdordate
    
    @property
    def e(self):
        return 0.016709 - 1.151E-9 * self.d
    
    @property
    def a(self):
        return 1
    
    @property
    def i(self):
        return 0
    
    @property
    def N(self):
        return 0
    
    @property
    def w(self):
        return 282.9404 + 4.70935E-5 * self.d
    
    @property
    def M(self):
        return 356.0470 + 0.9856002585 * self.d
    
    def cartesianCoordinates(self,geocentric=False):
        """
        Returns the ecliptic coordinates of the Sun at the date/time given by
        :attr:`jd` as an (x,y,z) tuple (in AU) .
        """
        if geocentric:
            from .obstools import jd_to_epoch
            from math import radians,cos,sin,atan2,sqrt
            
            #now get the necessary elements
            Mr = radians(self.M)
            wr = radians(self.w)
            e = self.e
            
            #compute coordinates
            #approximate eccentric anamoly
            E = Mr + e*sin(Mr)*(1.0 + e*cos(Mr))
            
            xv = cos(E) - e
            yv = sqrt(1.0 - e*e) * sin(E)
            
            v = atan2(yv,xv)
            r = sqrt(xv*xv + yv*yv)
            
            lsun = v + wr
            xs = r*cos(lsun)
            ys = r*sin(lsun)
            
            return xs,ys,0
        else:
            return 0,0,0
    
    def equatorialCoordinates(self):
        """
        Returns the equatorial coordinates of the Sun at the current date/time
        as a :class:`EquatorialCoordinates` object for the epoch at which they are
        derived.
        """
        from math import radians,degrees,cos,sin,atan2,sqrt
        from obstools import jd_to_epoch
        
        if hasattr(self,'_eqcache') and self._eqcache[0] == self._jd:
            return EquatorialCoordinates(*self._eqcache[1:],epoch=jd_to_epoch(self._jd))
        
        xs,ys,zs = self.cartesianCoordinates(True) #geocentric location
        
        eclr = radians(self._obliquity(self.jd))
        
        x = xs
        y = ys*cos(eclr)  
        z = ys*sin(eclr)
        
        ra = degrees(atan2(y,x))
        dec = degrees(atan2(z,sqrt(x*x+y*y)))
        
        #cache for faster retrieval if JD is not changed
        self._eqcache = (self._jd,ra,dec)
        return EquatorialCoordinates(ra,dec,epoch=jd_to_epoch(self._jd))
    
    

class Moon(KeplerianOrbit):
    """
    Orbital Elements for Earth's Moon
    """
    
    _validrange = (2415021.0,2488070.0)
    
    def __init__(self,jd=None):    
        """
        Initialize the object and optionally set the initial Julian Date (by
        default this is J2000)
        """    
        EphemerisObject.__init__(self,name='Luna',jd0=KeplerianOrbit.jd2000-0.5)
        
        if jd is None:
            self.jd = self.jd0 
        else:
            self.jd = jd
        
    @property
    def e(self):
        return 0.054900
    
    @property
    def a(self):
        return 0.00256955
    
    @property
    def i(self):
        return 5.1454
    
    @property
    def N(self):
        return 125.1228 - 0.0529538083 * self.d
    
    @property
    def w(self):
        return 318.0634 + 0.1643573223 * self.d
    
    @property
    def M(self):
        return 115.3654 + 13.0649929509 * self.d
    
    
    
    def cartesianCoordinates(self,geocentric=False):
        """
        Returns the ecliptic coordinates of the Moon at the date/time given by
        :attr:`jd` as an (x,y,z) tuple (in AU) .
        """
        
        
        xg,yg,zg = KeplerianOrbit.cartesianCoordinates(self) #the orbital elements are for geocentric coordinates
        if geocentric:
            return xg,yg,zg
        else:
            xs,ys,zs = _sun_coords(jd)
            return xg-xs,yg-ys,zg-zs
    
    
    def phase(self,perc=False):
        """
        Compute the phase of the moon - 0 is "new", 1 is "full".
        
        if `perc` is True, returns percent illumination.
        """
        from math import sqrt,atan2
        
        xg,yg,zg = self.cartesianCoordinates(True)
        sun = solsysobj['sun']
        oldsunjd = sun.jd
        sun.jd = self.jd
        xs,ys,zs = sun.cartesianCoordinates()
        sun.jd = oldsunjd
        
        longsun = atan2(ys,xs)
        longmoon = atan2(yg,xg)
        latmoon = atan2(zh,sqrt(xg*xg + yg*yg))
        
        phase = (1 + cos(longsun - longmoon)*cos(latmoon))/2
        
        if perc:
            return 100*phase
        else:
            return phase
        
#now generate the registry of solar system objects
solsysobjs = DataObjectRegistry('object',KeplerianOrbit)
solsysobjs['sun'] = Sun()
solsysobjs['moon'] = Moon()

#all of these from http://stjarnhimlen.se/comp/ppcomp.html#4
solsysobjs['mercury'] = KeplerianOrbit('Mercury',
                        e=lambda d: 0.205635 + 5.59E-10 * d,
                        a=0.387098,
                        i=lambda d: 7.0047 + 5.00E-8 * d,
                        N=lambda d: 48.3313 + 3.24587E-5 * d,
                        w=lambda d: 29.1241 + 1.01444E-5 * d,
                        M=lambda d: 168.6562 + 4.0923344368 * d,
                        jd0=KeplerianOrbit.jd2000 - 0.5)
solsysobjs['mercury']._validrange = solsysobjs['sun']._validrange

solsysobjs['venus'] = KeplerianOrbit('Venus',
                        e=lambda d: 0.006773 - 1.302E-9 * d,
                        a=0.723330,
                        i=lambda d: 3.3946 + 2.75E-8 * d,
                        N=lambda d: 76.6799 + 2.46590E-5 * d,
                        w=lambda d: 54.8910 + 1.38374E-5 * d,
                        M=lambda d: 48.0052 + 1.6021302244 * d,
                        jd0=KeplerianOrbit.jd2000 - 0.5)
solsysobjs['venus']._validrange = solsysobjs['sun']._validrange    

solsysobjs['mars'] = KeplerianOrbit('Mars',
                        e=lambda d: 0.093405 + 2.516E-9 * d,
                        a=1.523688,
                        i=lambda d: 1.8497 - 1.78E-8 * d,
                        N=lambda d: 49.5574 + 2.11081E-5 * d,
                        w=lambda d: 286.5016 + 2.92961E-5 * d,
                        M=lambda d: 18.6021 + 0.5240207766 * d,
                        jd0=KeplerianOrbit.jd2000 - 0.5)
solsysobjs['mars']._validrange = solsysobjs['sun']._validrange

solsysobjs['jupiter'] = KeplerianOrbit('Jupiter',
                        e=lambda d: 0.048498 + 4.469E-9 * d,
                        a=5.20256,
                        i=lambda d: 1.3030 - 1.557E-7 * d,
                        N=lambda d: 100.4542 + 2.76854E-5 * d,
                        w=lambda d: 273.8777 + 1.64505E-5 * d,
                        M=lambda d: 19.8950 + 0.0830853001 * d,
                        jd0=KeplerianOrbit.jd2000 - 0.5)
solsysobjs['jupiter']._validrange = solsysobjs['sun']._validrange

solsysobjs['saturn'] = KeplerianOrbit('Saturn',
                        e=lambda d: 0.055546 - 9.499E-9 * d,
                        a=9.55475,
                        i=lambda d: 2.4886 - 1.081E-7 * d,
                        N=lambda d: 113.6634 + 2.38980E-5 * d,
                        w=lambda d: 339.3939 + 2.97661E-5 * d,
                        M=lambda d:  316.9670 + 0.0334442282 * d,
                        jd0=KeplerianOrbit.jd2000 - 0.5)
solsysobjs['saturn']._validrange = solsysobjs['sun']._validrange

solsysobjs['uranus'] = KeplerianOrbit('Uranus',
                        e=lambda d: 0.047318 + 7.45E-9 * d,
                        a=lambda d: 19.18171 - 1.55E-8 * d,
                        i=lambda d: 0.7733 + 1.9E-8 * d,
                        N=lambda d: 74.0005 + 1.3978E-5 * d,
                        w=lambda d: 96.6612 + 3.0565E-5 * d,
                        M=lambda d: 142.5905 + 0.011725806 * d,
                        jd0=KeplerianOrbit.jd2000 - 0.5)
solsysobjs['uranus']._validrange = solsysobjs['sun']._validrange

solsysobjs['neptune'] = KeplerianOrbit('Neptune',
                        e=lambda d: 0.008606 + 2.15E-9 * d,
                        a=lambda d: 30.05826 + 3.313E-8 * d,
                        i=lambda d: 1.7700 - 2.55E-7 * d,
                        N=lambda d: 131.7806 + 3.0173E-5 * d,
                        w=lambda d: 272.8461 - 6.027E-6 * d,
                        M=lambda d: 260.2471 + 0.005995147 * d,
                        jd0=KeplerianOrbit.jd2000 - 0.5)
solsysobjs['neptune']._validrange = solsysobjs['sun']._validrange

def _earth_coords(jd):
    """
    Coordinates of the earth in heliocentric cartesian coordinates.  Can also
    be thought of as the negative of the sun coordinates in geocentric.
    """
    try:
        sun = solsysobjs['sun']
        oldsunjd = sun.jd
        sun.jd = self.jd
        xs,ys,zs = sun.cartesianCoordinates(True)
        return -xs,-ys,-zs
    finally:
        sun.jd = oldsunjd
    
#<--------------------functional coordinate transforms------------------------->
def cartesian_to_polar(x,y,degrees=False):
    """
    Converts arrays in 2D rectangular Cartesian coordinates to polar
    coordinates.
    
    :param x: First cartesian coordinate
    :type x: :class:`numpy.ndarray`
    :param y: Second cartesian coordinate
    :type y: :class:`numpy.ndarray`
    :param degrees: 
        If True, the output theta angle will be in degrees, otherwise radians.
    :type degrees: boolean
    
    :returns: 
        (r,theta) where theta is measured from the +x axis increasing towards
        the +y axis
    """
    r = (x*x+y*y)**0.5
    t = np.arctan2(y,x)
    if degrees:
        t = np.degrees(t)
    
    return r,t

def polar_to_cartesian(r,t,degrees=False):
    """
    Converts arrays in 2D polar coordinates to rectangular cartesian
    coordinates.
    
    Note that the spherical coordinates are in *physicist* convention such that
    (1,0,pi/2) is x-axis.
    
    :param r: Radial coordinate
    :type r: :class:`numpy.ndarray`
    :param t: Azimuthal angle from +x-axis increasing towards +y-axis
    :type t: :class:`numpy.ndarray`
    :param degrees: 
        If True, the input angles will be in degrees, otherwise radians.
    :type degrees: boolean
    
    :returns: arrays (x,y)
    """
    if degrees:
        t=np.radians(t)
        
    return r*np.cos(t),r*np.sin(t)

def cartesian_to_spherical(x,y,z,degrees=False):
    """
    Converts three arrays in 3D rectangular cartesian coordinates to
    spherical polar coordinates.
    
    Note that the spherical coordinates are in *physicist* convention such that
    (1,0,pi/2) is x-axis.
    
    :param x: First cartesian coordinate
    :type x: :class:`numpy.ndarray`
    :param y: Second cartesian coordinate
    :type y: :class:`numpy.ndarray`
    :param z: Third cartesian coordinate
    :type z: :class:`numpy.ndarray`
    :param degrees: 
        If True, the output theta angle will be in degrees, otherwise radians.
    :type degrees: boolean
    
    :returns: arrays (r,theta,phi) 
    """
    xsq,ysq,zsq=x*x,y*y,z*z
    r=(xsq+ysq+zsq)**0.5
    #t=np.arccos(z,r) #TODO:check to make even more efficient
    t=np.arctan2((xsq+ysq)**0.5,z)
    p=np.arctan2(y,x)
    if degrees:
        t,p=np.degrees(t),np.degrees(p)
    return r,t,p

def spherical_to_cartesian(r,t,p,degrees=False):
    """
    Converts arrays in 3D spherical polar coordinates to rectangular cartesian
    coordinates.
    
    Note that the spherical coordinates are in *physicist* convention such that
    (1,0,pi/2) is x-axis.
    
    :param r: Radial coordinate
    :type r: :class:`numpy.ndarray`
    :param t: Colatitude (angle from z-axis)
    :type t: :class:`numpy.ndarray`
    :param p: Azimuthal angle from +x-axis increasing towards +y-axis
    :type p: :class:`numpy.ndarray`
    :param degrees: 
        If True, the input angles will be in degrees, otherwise radians.
    :type degrees: boolean
    
    :returns: arrays (x,y,z)
    """
    if degrees:
        t,p=np.radians(t),np.radians(p)
    x=r*np.sin(t)*np.cos(p)
    y=r*np.sin(t)*np.sin(p)
    z=r*np.cos(t)
    
    return x,y,z

def latitude_to_colatitude(lat,degrees=False):
    """
    converts from latitude  (i.e. 0 at the equator) to colatitude/inclination 
    (i.e. "theta" in physicist convention).
    """
    if degrees:
        return 90 - lat
    else:
        return pi/2 - lat

def colatitude_to_latitude(theta,degrees=False):
    """
    converts from colatitude/inclination (i.e. "theta" in physicist convention) 
    to latitude (i.e. 0 at the equator).
    """
    if degrees:
        return 90 - theta
    else:
        return pi/2 - theta

def cartesian_to_cylindrical(x,y,z,degrees=False):
    """
    Converts three arrays in 3D rectangular Cartesian coordinates
    to cylindrical polar coordinates. 
    
    if degrees is true, outputtheta is in degrees, otherwise radians
    returns s,theta,z (theta increasing from +x to +y, 0 at x-axis)
    """
    s,t = cartesian_to_polar(x,y)
    return s,t,z
    
def cylindrical_to_cartesian(s,t,z,degrees=False):
    """
    Converts three arrays in cylindrical polar coordinates to
    3D rectangular Cartesian coordinates. 
    
    if degrees is true, converts from degrees to radians for theta
    returns x,y,z (theta increasing from +x to +y, 0 at x-axis)
    """
    x,y = polar_to_cartesian(s,t,degrees)
    return x,y,z
    
def offset_proj_sep(rx,ty,pz,offset,spherical=False):
    """
    computes the projected seperation for a list of points in galacto-centric
    coordinates as seen from a point offset (an [[x,y,z]] 2-sequence)
    
    spherical determines if the inputs are spherical coords or cartesian.  If it
    is 'degrees', spherical coordinates will be used, converting from degrees to
    radians
    """
    if spherical is 'degrees':
        x,y,z=spherical_to_cartesian(rx,ty,pz,True)
    elif spherical:
        x,y,z=spherical_to_cartesian(rx,ty,pz,False)
    else:
        x,y,z=rx,ty,pz
    
    offset=np.array(offset)
    if offset.shape[1]!=3 or len(offset.shape)!=2:
        raise ValueError('offset not a sequnce of 3-sequence')
    
    ohat=(offset.T*np.sum(offset*offset,1)**-0.5)
    return np.array(np.matrix(np.c_[x,y,z])*np.matrix(ohat))


def sky_sep_to_3d_sep(pos1,pos2,d1,d2):
    """
    Compute the full 3D seperation between two objects at distances `d1` and
    `d2` and angular positions `pos1` and `pos2` (:class:`LatLongCoordinates`
    objects, or an argument that will be used to generate a
    :class:`EquatorialCoordinates` object)
    
    :param pos1: on-sky position of first object
    :type pos1: :class:`LatLongCoordinates` or initializer
    :param pos2: on-sky position of second object
    :type pos2: :class:`LatLongCoordinates` or initializer
    :param d1: distance to first object
    :type d1: scalar
    :param d2: distance to second object
    :type d2: scalar
    
    .. testsetup::
    
        from astropysics.coords import sky_sep_to_3d_sep
    
    .. doctest::
        >>> p1 = LatLongCoordinates(0,0)
        >>> p2 = LatLongCoordinates(0,10)
        >>> '%.10f'%sky_sep_to_3d_sep(p1,p2,20,25)
        '6.3397355613'
        >>> '%.10f'%sky_sep_to_3d_sep('0h0m0s +0:0:0','10:20:30 +0:0:0',1,2)
        '2.9375007333'
        
    """    
    if not isinstance(pos1,LatLongCoordinates):
        pos1 = EquatorialCoordinates(pos1)
    if not isinstance(pos2,LatLongCoordinates):
        pos2 = EquatorialCoordinates(pos2)
        
    return (pos1-pos2).seperation3d(d1,d2)

def radec_str_to_decimal(ra,dec):
    if isinstance(ra,basestring):
        if not isinstance(dec,basestring):
            raise ValueError('either both ra and dec must be a strings or neither')
        
        ra = AngularCoordinate(ra,sghms=True).d
        dec = AngularCoordinate(dec,sghms=False).d
    else:
        if isinstance(dec,basestring):
            raise ValueError('either both ra and dec must be a strings or neither')   
        if len(ra) != len(dec):
            raise ValueError("length of ra and dec don't match")
        
        ras,decs=[],[]
        for r,d in zip(ra,dec):
            ras.append(AngularCoordinate(r,sghms=True).d)
            decs.append(AngularCoordinate(d,sghms=False).d)
        ra,dec = ras,decs
    return ra,dec

def match_coords(a1,b1,a2,b2,eps=1,multi=False):
    """
    Match one coordinate array to another within a specified tolerance. Distance
    is determined by the cartesian distance between the two arrays added in 
    quadrature.
    
    :param a1: the first coordinate for the first set of coordinates
    :type a1: 1D :class:`numpy.ndarray`
    :param a2: the second coordinate for the first set of coordinates
    :type a2: 1D :class:`numpy.ndarray`
    :param a1: the first coordinate for the second set of coordinates
    :type a1: 1D :class:`numpy.ndarray`
    :param a2: the second coordinate for the second set of coordinates
    :type a2: 1D :class:`numpy.ndarray`
    :param multi:
        Determines behavior if more than one coordinate pair matches.  Can be:
        
        * True: raise an exception if more than one match is found
        * 'warn': a warning will be issued if more than one match is found
        * 'print': a statement will be printed  if more than one match is found
        * 'full': the 2D array with matches as booleans along the axes will be returned
        * 'count': a count of matches will be returned instead of a mask
        * 'index': a list of match indecies will be returned instead of a mask
        * False: do nothing - just return if something matched
    
    :returns: 
        (mask of matches for array 1, mask of matches for array 2) or as
        described in the corresponding `multi` parameter value
    
    **Examples**
    .. testsetup::
    
        from astropysics.coords import match_coords
        from numpy import array
    
    .. doctest::
        >>> ra1 = array([1,2,3,4])
        >>> dec1 = array([0,0,0,0])
        >>> ra2 = array([7,6,5,4])
        >>> dec2 = array([.5,.5,.5,.5])
        >>> match_coords(ra1,dec1,ra2,dec2,1)
        (array([False, False, False,  True], dtype=bool), array([False, False, 
        False,  True], dtype=bool))
    """
    def find_sep(A,B):
        At = np.tile(A,(len(B),1))
        Bt = np.tile(B,(len(A),1))
        return At.T-Bt
    sep1=find_sep(a1,a2)
    sep2=find_sep(b1,b2)
    
    matches = (sep1*sep1+sep2*sep2)**0.5 < eps
    if multi:
        if multi == 'full':
            return matches.T
        elif multi == 'count':
            return np.sum(np.any(matches,axis=1)),np.sum(np.any(matches,axis=0)) 
        elif multi == 'index':
            return np.where(matches)
        elif multi == 'warn':
            s1,s2 = np.sum(matches,axis=1),np.sum(matches,axis=0) 
            from warnings import warn
            
            for i in np.where(s1>1)[0]:
                warn('1st index %i has %i matches!'%(i,s1[i]))
            for j in np.where(s2>1)[0]:
                warn('2nd index %i has %i matches!'%(j,s2[j]))
            return s1>0,s2>0
        elif multi == 'print':
            s1,s2 = np.sum(matches,axis=1),np.sum(matches,axis=0) 
            
            for i in np.where(s1>1)[0]:
                print '1st index',i,'has',s1[i],'matches!'
            for j in np.where(s2>1)[0]:
                print '2nd index',j,'has',s2[j],'matches!'
            return s1>0,s2>0
        else:
            raise ValueError('unrecognized multi mode')
    else:
        return np.any(matches,axis=1),np.any(matches,axis=0)
    
def seperation_matrix(v,w=None,tri=False):
    """
    This function takes a n(x?x?x?) array and produces an array given by
    A[i][j] = v[i]-v[j]. if w is not None, it produces A[i][j] = v[i]-w[j]
    
    If the input has more than 1 dimension, the first is assumed to be the 
    one to expand
    
    If tri is True, the lower triangular part of the matrix is set to 0
    (this is really only useful if w is None)
    """
    if w is None:
        w = v
    
    shape1 = list(v.shape)
    shape1.insert(1,1)
    shape2 = list(w.shape)
    shape2.insert(0,1)
    
    A = v.reshape(shape1)-w.reshape(shape2)
    
    if tri:
        return np.triu(A)
    else:
        return A
    

#<-----------------Cosmological distance and conversions ---------->
def cosmo_z_to_dist(z,zerr=None,disttype=0,inttol=1e-6,normed=False,intkwargs={}):
    """
    Calculates the cosmolgical distance to some object given a redshift.  Note
    that this uses H0,omegaM,omegaL, and omegaR from the current
    :class:`astropyscs.constants.Cosmology` -- if any of those do not exist in 
    the current cosmology this will fail.
    
    The distance type can be one of the following:
    
    * 'comoving'(0) : comoving distance (in Mpc)
    * 'luminosity'(1) : luminosity distance (in Mpc)
    * 'angular'(2) : angular diameter distance (in Mpc)
    * 'lookback'(3) : lookback time (in Gyr)
    * 'distmod'(4) : distance modulus
    
    :param z: The redshift at which to compute the distance
    :type z: array, scalar, or None
    :param zerr: Symmetric error in redshift
    :type zerr: array, scalar, or None
    :param disttype:
        The type of distance to compute -- may be any of the types described
        above.
    :type disttype: A string or int
    :param inttol: fractional precision of the output (used in integrals)
    :type inttol: A float<1
    :param normed: 
        If True, normalize output by result for `z` == None.  If a scalar, 
        normalize by the distance at that redshift. If False, no normalization.
    :type normed: boolean
    :param intkwargs: keywords for integrals (see :mod:`scipy.integrate`)
    :type intkwargs: a dictionary   
    
    
    :returns: 
        Distance of type selected by `disttype` in above units or normalized as
        controlled by `normed` parameter. If `zerr` is not None, the output is
        (z,zupper,zlower), otherwise just z.
    """
    from operator import isSequenceType
    from scipy.integrate import quad as integrate
    from numpy import array,vectorize,abs
    
    from .constants import H0,omegaM,omegaL,omegaR,c
    
    c=c/1e5 #convert to km/s
    if type(disttype) == str:
        disttypemap={'comoving':0,'luminosity':1,'angular':2,'lookback':3,'distmod':4}
        try:
            disttype=disttypemap[disttype]
        except KeyError,e:
            e.message='invalid disttype string'
            raise
    
    flipsign = disttype < 0
    disttype = abs(disttype)
    
    if omegaL+omegaM+omegaR != 1:
        from warnings import warn
        warn('cosmological parameters do not sum to 1 - algorithm may not be correct for non-flat universe')
    
    if z is None:
        if normed:
            return 1.0
        if disttype == 2:
            #find maximum value for angular diam dist
            from scipy.optimize import fminbound
            res = upper = 5
            while abs(res-upper) < inttol:
                #-2 flips sign so that we get a minimum instead of a maximum
                res = fminbound(cosmo_z_to_dist,0,upper,(None,-2,inttol,normed,intkwargs),inttol)
            return res
        else:
            #iterate towards large numbers until convergence achieved
            iterz=1e6
            currval=cosmo_z_to_dist(iterz,None,disttype,inttol,False,intkwargs)
            lastval=currval+2*inttol
            while(abs(lastval-currval)>inttol):
                lastval=currval
                iterz*=10
                currval=cosmo_z_to_dist(iterz,None,disttype,inttol,False,intkwargs)
            return currval
        
    z=array(z)
    a0=1/(z+1)
    omegaK=1-omegaM-omegaL-omegaR
    
    if disttype != 3:
        #comoving distance out to scale factor a0: integral(da'/(a'^2 H(a')),a0,1)
        #H^2 a^4=omegaR +omegaM a^1 + omegaE a^4 + omegaK a^2
        def integrand(a,H0,R,M,L,K): #1/(a^2 H)
            return (R + M*a + L*a**4 + K*a**2)**-0.5/H0
    else:
        #lookback time
        def integrand(a,H0,R,M,L,K): #1/(a^2 H)
            return a*(R + M*a + L*a**4 + K*a**2)**-0.5/H0
        
    if isSequenceType(a0):
        integratevec=vectorize(lambda x:integrate(integrand,x,1,args=(H0,omegaR,
                                             omegaM,omegaL,omegaK),**intkwargs))
        res=integratevec(a0)
        intres,interr=res[0],res[1]        
        try:
            if any(interr/intres > inttol):
                raise Exception('Integral fractional error for one of the integrals is beyond tolerance')
        except ZeroDivisionError:
            pass
        
    else:
        res=integrate(integrand,a0,1,args=(H0,omegaR,omegaM,omegaL,omegaK),**intkwargs)
        intres,interr=res[0],res[1]
        
        try:
            if interr/intres > inttol:
                raise Exception('Integral fractional error is '+str(interr/intres)+', beyond tolerance'+str(inttol))
        except ZeroDivisionError:
            pass
    
    if disttype == 0:
        d=c*intres
    elif disttype == 1:
        d=c*intres/a0
    elif disttype == 2:
        d=a0*c*intres
    elif disttype == 3:
        d=c*intres*3.26163626e-3
        #d=chi*3.08568025e19/24/3600/365.25e9
    elif disttype == 4:
        from .phot import distance_modulus
        d=distance_modulus(c*intres/a0*1e6,autocosmo=False)
        
    else:
        raise KeyError('unknown disttype')
    
    if normed:
            nrm=1/cosmo_z_to_dist(None if normed is True else normed,None,disttype,inttol,intkwargs)
    else:
        nrm=1
        
    if flipsign:
        nrm *= -1
        
    if zerr is None:
        return nrm*d
    else: 
        upper=cosmo_z_to_dist(z+zerr,None,disttype,inttol,intkwargs)
        lower=cosmo_z_to_dist(z-zerr,None,disttype,inttol,intkwargs)
        return nrm*d,nrm*(upper-d),nrm*(d-lower)
    
def cosmo_dist_to_z(d,derr=None,disttype=0,inttol=1e-6,normed=False,intkwargs={}):
    """
    Convert a distance to a redshift. See :func:`cosmo_z_to_dist` for meaning of
    parameters.
    """
    from scipy.optimize import brenth
    maxz=10000.0
    
    if derr is not None:
        raise NotImplementedError
    
    f=lambda z,dmin:dmin-cosmo_z_to_dist(z,None,disttype,inttol,normed,intkwargs)
    try:
        while f(maxz,d) > 0:
            maxz=maxz**2
    except OverflowError:
        raise ValueError('input distance %g impossible'%float(d))
        
    zval = brenth(f,0,maxz,(d,),xtol=inttol)
    
    return zval
    
    
def cosmo_z_to_H(z,zerr=None):
    """
    Calculates the hubble constant as a function of redshift for the current
    :class:`astropysics.constant.Cosmology` .  
    
    :param z: redshift
    :type z: scalar or array-like
    :param zerr: uncertainty in redshift 
    :type zerr: scalar, array-like, or None
    
    :returns: 
        Hubble constant for the given redshift, or (H,upper_error,lower_error)
        if `zerr` is not None
    """
    from .constants import get_cosmology
    c = get_cosmology()
    if zerr is None:
        return c.H(z)
    else:
        H=c.H(z)
        upper=c.H(z+zerr)
        lower=c.H(z-zerr)
        return H,upper-H,lower-H

def angular_to_physical_size(angsize,zord,usez=True,**kwargs):
    """
    Converts an observed angular size (in arcsec or as an AngularSeperation 
    object) to a physical size.
    
    kwargs are passed into :func:`cosmo_z_to_dist` if `usez` is True.
    
    :param angsize: 
        Angular size in arcsecond or an :class:`AngularSeperation` object.
    :param zord: Redshift or distance
    :type zord: scalar number
    :param usez:
        If True, the input will be interpreted as a redshift, and kwargs
        will be passed into the distance calculation. The result will be in
        pc. Otherwise, `zord` will be interpreted as a distance.
    :type usez: boolean
    
    :returns: a scalar value for the physical size (in pc if redshift is used) 
    """
    if usez:
        d = cosmo_z_to_dist(zord,disttype=2,**kwargs)*1e6 #pc
    else:
        if len(kwargs)>0:
            raise TypeError('if not using redshift, kwargs should not be provided')
        d = zord
    
    if hasattr(angsize,'arcsec'):
        angsize = angsize.arcsec
    sintheta = np.sin(angsize/206265)
    return d*(1/sintheta/sintheta-1)**-0.5
    #return angsize*d/206265

def physical_to_angular_size(physize,zord,usez=True,objout=False,**kwargs):
    """
    converts a physical size (in pc) to an observed angular size (in arcsec or 
    as an AngularSeperation object if objout is True)
    
    if usez is True, zord is interpreted as a redshift, and cosmo_z_to_dist 
    is used to determine the distance, with kwargs passed into cosmo_z_to_dist 
    otherwise, zord is taken directly as a angular diameter distance (in pc) 
    and kwargs should be absent
    """
    if usez:
        d = cosmo_z_to_dist(zord,disttype=2,**kwargs)*1e6 #pc
    else:
        if len(kwargs)>0:
            raise TypeError('if not using redshift, kwargs should not be provided')
        d = zord
        
    r=physize
    res = 206265*np.arcsin(r*(d*d+r*r)**-0.5)
    if objout:
        return AngularSeperation(res/3600)
    else:
        return res
    
    
#<---------------------DEPRECATED transforms----------------------------------->

#galactic coordate reference positions from IAU 1959 and wikipedia
_galngpJ2000=EquatorialCoordinates('12h51m26.282s','+27d07m42.01s')
_galngpB1950=EquatorialCoordinates('12h49m0s','27d24m0s')
_gall0J2000=122.932
_gall0B1950=123

def celestial_transforms(ai,bi,transtype=1,epoch='J2000',degin=True,degout=True):
    """
    Use this to transform between Galactic,Equatorial, and Ecliptic coordinates
    
    transtype can be a number from the table below, or 'ge','eg','gq','qg','gc',
    'cg','cq','qc'
    transtype   From           To       |  transtype    From         To
        1     RA-Dec (2000)  Galactic   |     4       Ecliptic      RA-Dec    
        2     Galactic       RA-DEC     |     5       Ecliptic      Galactic  
        3     RA-Dec         Ecliptic   |     6       Galactic      Ecliptic
        
    adapted from IDL procedure EULER 
    (http://astro.uni-tuebingen.de/software/idl/astrolib/astro/euler.html)
    """
    #   J2000 coordinate conversions are based on the following constants
    #   (see the Hipparcos explanatory supplement).
    #  eps = 23.4392911111d              Obliquity of the ecliptic
    #  alphaG = 192.85948d               Right Ascension of Galactic North Pole
    #  deltaG = 27.12825d                Declination of Galactic North Pole
    #  lomega = 32.93192d                Galactic longitude of celestial equator  
    #  alphaE = 180.02322d              Ecliptic longitude of Galactic North Pole
    #  deltaE = 29.811438523d            Ecliptic latitude of Galactic North Pole
    #  Eomega  = 6.3839743d              Galactic longitude of ecliptic equator   
    
    from warnings import warn
    warn('celestial_transforms function is deprecated - use general coordinate transform framework',DeprecationWarning)           

    if epoch == 'B1950':
            psi   = ( 0.57595865315, 4.9261918136,0, 0,0.11129056012, 4.7005372834)     
            stheta =( 0.88781538514,-0.88781538514, 0.39788119938,-0.39788119938, 0.86766174755,-0.86766174755)    
            ctheta =( 0.46019978478, 0.46019978478,0.91743694670, 0.91743694670, 0.49715499774, 0.49715499774)    
            phi =   ( 4.9261918136,  0.57595865315,  0, 0,  4.7005372834, 0.11129056012)

    elif epoch == 'J2000':
            psi   = ( 0.57477043300,4.9368292465,0,0,0.11142137093, 4.71279419371)     
            stheta =( 0.88998808748,-0.88998808748,  0.39777715593,-0.39777715593, 0.86766622025,-0.86766622025)   
            ctheta =( 0.45598377618, 0.45598377618, 0.91748206207, 0.91748206207,  0.49714719172, 0.49714719172)    
            phi  =  ( 4.9368292465,  0.57477043300,  0, 0,        4.71279419371, 0.11142137093)
    else:
            raise ValueError('unknown epoch')
            
    from math import pi
    from numpy import array,sin,cos,arcsin,arctan2
    twopi   =   2.0*pi
    fourpi  =   4.0*pi
    deg_to_rad = 180.0/pi
    
    
    if degin:
        ai,bi=array(ai),array(bi)
    else:
        ai,bi=np.degrees(ai),np.degrees(bi)
    
    if type(transtype) == int:
        i = transtype - 1
    else:
        transd={'ge':1,'eg':0,'gq':1,'qg':0,'gc':5,'cg':4,'cq':3,'qc':2}
        i  = transd[transtype]
    a  = ai/deg_to_rad - phi[i]
    b = bi/deg_to_rad
    sb = sin(b) 
    cb = cos(b)
    cbsa = cb * sin(a)
    b  = -stheta[i] * cbsa + ctheta[i] * sb
    try:
            b[b>1.0]=1.0
    except TypeError: #scalar
            if b > 1:
                    b=array(1.0)
    bo = arcsin(b)*deg_to_rad
    a =  arctan2( ctheta[i] * cbsa + stheta[i] * sb, cb * cos(a) )
    ao = ( (a+psi[i]+fourpi) % twopi) * deg_to_rad
    
    if not degout:
        ao,bo = np.radians(ao),np.radians(bo)
    
    return ao,bo

_B1950toJ2000xyz=np.matrix([[0.999926,  -0.011179,  -0.004859],
                            [0.011179,   0.999938,  -0.000027],
                            [0.004859,   0.000027,   0.999988]])

def epoch_transform(ra,dec,inepoch='B1950',outepoch='J2000',degrees=True):
    from warnings import warn
    warn('epoch_transform function is deprecated - use general coordinate transform framework',DeprecationWarning)
    
    if inepoch != 'B1950' and inepoch != 'J2000':
        raise ValueError('unrecognized epoch '+inepoch)
    if outepoch != 'B1950' and outepoch != 'J2000':
        raise ValueError('unrecognized epoch '+outepoch)
    if degrees:
        ra,dec=np.radians(ra),np.radians(dec)
    else:
        ra,dec=np.array(ra),np.array(dec)
    
    if inepoch == outepoch:
        trans=np.matrix(np.eye(3))
    elif inepoch == 'B1950' and outepoch == 'J2000':
        trans=_B1950toJ2000xyz
    elif inepoch == 'J2000' and outepoch == 'B1950':
        trans=_B1950toJ2000xyz.I
    else:
        raise ('unrecognized epochs')
    
    x=np.cos(ra)*np.cos(dec)
    y=np.sin(ra)*np.cos(dec)
    z=np.sin(dec)
    
    v=np.matrix((x,y,z))
    xp,yp,zp=trans*v
    
    rap=np.arctan2(yp,xp)
    decp=np.arcsin(zp)
    
    return rap,decp

def galactic_to_equatorial(l,b,epoch='J2000',strout=None):
    """
    convinience function for celestial_transforms
    if strout is None, will automatically decide based on inputs
    """
    from warnings import warn
    warn('galactic_to_equatorial function is deprecated - use general coordinate transform framework',DeprecationWarning)
    
    from operator import isSequenceType
    
    if type(l) == str:
        l=AngularCoordinate(l).degrees
        if strout is None:
            strout=True
    if type(b) == str:
        b=AngularCoordinate(b).degrees
        if strout is None:
            strout=True
    ra,dec = celestial_transforms(l,b,transtype='ge',epoch=epoch)
    if strout:
        if not isSequenceType(ra):
            ra=[ra]
        if not isSequenceType(dec):
            dec=[dec]
        rao,deco=[],[]
        for rai in ra:
            rao.append(AngularCoordinate(rai).getHmsStr())
        for deci in dec:
            deco.append(AngularCoordinate(deci).getDmsStr())
        return rao,deco
    else:
        return ra,dec
    
    
def equatorial_to_galactic(ra,dec,epoch='J2000',strout=None):
    """
    convinience function for celestial_transforms
    if strout is None, will automatically decide based on inputs
    """
    from warnings import warn
    warn('equatorial_to_galactic function is deprecated - use general coordinate transform framework',DeprecationWarning)
    
    from operator import isSequenceType
    
    if type(ra) == str:
        ra=AngularCoordinate(ra).degrees
        if strout is None:
            strout=True
    if type(dec) == str:
        dec=AngularCoordinate(dec).degrees
        if strout is None:
            strout=True
    l,b = celestial_transforms(ra,dec,transtype='eg',epoch=epoch)
    if strout:
        if not isSequenceType(l):
            l=[l]
        if not isSequenceType(b):
            b=[b]
        lo,bo=[],[]
        for li in l:
            lo.append(AngularCoordinate(li).getDmsStr())
        for bi in b:
            bo.append(AngularCoordinate(bi).getDmsStr())
        return lo,bo
    else:
        return l,b

#clean namespace
del abstractmethod,ABCMeta