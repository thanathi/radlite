import os
import numpy as np
import matplotlib.pylab as plt
import matplotlib.ticker as ticker
from mpl_toolkits.axes_grid1 import make_axes_locatable

from scipy.integrate import cumtrapz

import radmc as radmc

def cbfmt(x, pos):
    a, b = '{:.1e}'.format(10**x).split('e')
    b = int(b)
    return r'${} \times 10^{{{}}}$'.format(a, b)

class radlite_model(radmc.radmc_model):
    def __init__(self,path):
        
        self.au = 1.49597871e13
        self.molweight = 1.66053892e-24*2.3
        
        radmc.radmc_model.__init__(self,path)
        self.abundance,self.abundance_collpartner = self.read_abundance()
        self.gastemperature = self.read_gastemperature()

    def read_abundance(self):
        filename = 'abundance.inp'
        fullpath = os.path.join(self.path,filename)
        file = open(fullpath,'r')

        nr,nt = file.readline().split()
        nr = int(nr)
        nt = int(nt)
      
        abundance = np.zeros((nr,nt*2))
        abundance_collpartner = np.zeros((nr,nt*2))
        i = 0
        j = 0
        for l in file:
            if not l.isspace():
                abun_str,collabun_str = l.split()
                abundance[j,i] = float(abun_str)
                abundance_collpartner[j,i] = float(collabun_str)
                if i==nt-1:
                    abundance[j,i+1:] = abundance[j,nt-1::-1]
                    abundance_collpartner[j,i+1:] = abundance_collpartner[j,nt-1::-1]
                    i = 0
                    j += 1
                else:
                    i += 1
                    
        file.close()
        
        return abundance,abundance_collpartner

    def read_gastemperature(self):
        filename = 'temperature.inp'
        fullpath = os.path.join(self.path,filename)
        file = open(fullpath,'r')

        nr,nt,dum = file.readline().split()
        nr = int(nr)
        nt = int(nt)
      
        gastemperature = np.zeros((nr,nt*2))
        i = 0
        j = 0
        for l in file:
            if not l.isspace():
                gastemperature[j,i] = float(l)
                if i==nt-1:
                    gastemperature[j,i+1:] = gastemperature[j,nt-1::-1]
                    i = 0
                    j += 1
                else:
                    i += 1
                    
        file.close()
        
        return gastemperature
        
    def surface_at_column(self,column,au=False):
        cum = cumtrapz(self.gasdensity*self.abundance/(1.66053892e-24*2.3),-self.y,initial=0.)
        ys = np.zeros(self.nr)
        for i in np.arange(self.nr):
            csub = np.argmin(np.abs(cum[i,:].flatten()-column))
            ys[i] = self.y[i,csub]
        
        if au:
            return (self.radius/self.au,ys/self.au)        
        else:
            return (self.radius,ys)
    
    def plot_quantity(self,type='gasdensity',plotfile=None,vmax=None,vmin=None,
                      length_unit='au',dens_unit='number',xlim=None,xlog=False,ylog=False,
                      ylim=None,nlevels=50,curves=None,isotropic=False,colors=None,linestyles=None):
        
        if length_unit is 'au':
            scale_length = self.au
                        
        if type is 'gasdensity':
            clabel = 'Gas density [$g/cm^3$]'
            quantity = self.gasdensity
            if dens_unit is 'number':
                scale_dens = self.molweight
                quantity /= scale_dens
                clabel = 'Gas density [$cm^{-3}$]'
            
        if type is 'abundance':
            clabel = 'H$_2$O abundance [100/g2d H${_2}^{-1}$]'
            quantity = self.abundance

        if type is 'dusttemperature':
            clabel = 'Dust temperature [K]'
            quantity = self.dusttemperature[:,:,0]

        if type is 'gastemperature':
            clabel = 'Gas temperature [K]'
            self.gastemperature[self.abundance<1e-10] = np.nan
            quantity = self.gastemperature
            
            
        
        if vmax is None:
            vmax = np.max(quantity)
        if vmin is None:
            vmin = np.min(quantity)
            
        if plotfile is None:
            plotfile = type+'.pdf'

        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.set_xlabel('Disk radius [AU]')
        ax.set_ylabel('Disk height [AU]')
        
        levels = np.linspace(np.log10(vmin),np.log10(vmax),nlevels)
        fc = ax.contourf(self.x/scale_length,self.y/scale_length,np.log10(quantity),levels=levels,\
                    extend='both',cmap=plt.cm.jet,aspect='equal')
        cc = ax.contour(self.x/scale_length,self.y/scale_length,np.log10(quantity),levels=[np.log10(1e4)],\
                    extend='both')

        plt.clabel(cc,inline=True)

        if xlim is not None:
            ax.set_xlim(xlim)
        if ylim is not None:
            ax.set_ylim(ylim)
        if xlog:
            ax.set_xscale('log')
        if ylog:
            ax.set_yscale('log')
        if isotropic:
            ax.set_aspect('equal')
                       
        if curves is not None:
            if colors is None:
                ncurves = len(curves)
                colors = ['darkred'] * ncurves
            if linestyles is None:
                nl = len(linestyles)
                linestyles = ['-'] * nl
            for curve,color,linestyle in zip(curves,colors,linestyles):
                ax.plot(curve[0],curve[1],lw=2., color=color, linestyle=linestyle)
 
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="3%", pad=0.1)
        fig.colorbar(fc,orientation='vertical',cax=cax,label=clabel, format=ticker.FuncFormatter(cbfmt))

        fig.tight_layout()
       

        fig.savefig(plotfile)
        
class line_spectra():
    def __init__(self, path):
        self.path = path
        
    def read_thread(self,thread):
        filename = 'linespectrum_moldata_'+str(thread)+'.dat'
        fullpath = os.path.join(self.path,filename)
        file = open(fullpath,'r')
        
        dum = file.readline()
        dum = file.readline()
        moldata_base = file.readline()
        moldata_file = file.readline()
        nlines = int(file.readline())
        nfreq = int(file.readline())
        deltav,vzero,incl = file.readline().split()
        lines = []
        for i in np.arange(nlines):
            file.readline()
            upper,lower = file.readline().strip().split()
            upper = int(upper)
            lower = int(lower)
            freq = float(file.readline())
            freq = float(freq)
            vzero = float(file.readline())
            nfreq = int(file.readline())
            
            vels = np.zeros(nfreq)
            fluxes = np.zeros(nfreq)

            file.readline()
            for j in np.arange(nfreq):
                vel,flux = file.readline().strip().split()
                vels[j] = float(vel)
                fluxes[j] = float(flux)

            lines.append({'velocity':vels,'flux':fluxes,'freq':freq,'upper':upper,'lower':lower})
        
        return lines
        
    def read_allthreads(self):
        pass