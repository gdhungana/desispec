"""
boxcar extraction for Spectra from Desi Image
"""
import numpy as np

def do_boxcar(image,psf,boxwidth=2.5,dw=0.5,nspec=500):
    """
    Extracts spectra row by row, given the centroids  
    Args:  
         image  : desispec.image object 
         psf: desispec.psf.PSF like object
              Or do we just parse the traces here and write a separate wrapper to handle this? Leaving psf in the input argument now.           
         boxwidth: HW box size in pixels
         dw: constant wavelength grid spacing in the output spectra 
    Returns desispec.frame.Frame object
    """
    import math
    from desispec.frame import Frame

    #wavelength=psf.wavelength() # (nspec,npix_y)
    wmin=psf.wmin
    wmax=psf.wmax
    waves=np.arange(wmin,wmax,0.25)
    xs=psf.x(None,waves) #- xtraces # doing the full image here.
    ys=psf.y(None,waves) #- ytraces 

    camera=image.camera
    spectrograph=int(camera[1:]) #- first char is "r", "b", or "z"
    mask=np.zeros(image.pix.T.shape)
    maxx,maxy=mask.shape
    maxx=maxx-1
    maxy=maxy-1
    ranges=np.zeros((mask.shape[1],xs.shape[0]+1),dtype=int)
    for bin in xrange(0,len(waves)):
        ixmaxold=0
        for spec in xrange(0,xs.shape[0]):
            xpos=xs[spec][bin]
            ypos=int(ys[spec][bin])
            if xpos<0 or xpos>maxx or ypos<0 or ypos>maxy : 
                continue 
            xmin=xpos-boxwidth
            xmax=xpos+boxwidth
            ixmin=int(math.floor(xmin))
            ixmax=int(math.floor(xmax))
            if ixmin <= ixmaxold:
                print "Error Box width overlaps,",xpos,ypos,ixmin,ixmaxold
                return None,None
            ixmaxold=ixmax
            if mask[int(xpos)][ypos]>0 :
                continue
        # boxing in x vals
            if ixmin < 0: #int value is less than 0
                ixmin=0
                rxmin=1.0
            else:# take part of the bin depending on real xmin
                rxmin=1.0-xmin+ixmin
            if ixmax>maxx:# xmax is bigger than the image
                ixmax=maxx
                rxmax=1.0
            else: # take the part of the bin depending on real xmax
                rxmax=xmax-ixmax
            ranges[ypos][spec+1]=math.ceil(xmax)#end at next column
            if  ranges[ypos][spec]==0:
                ranges[ypos][spec]=ixmin
            mask[ixmin][ypos]=rxmin
            for x in xrange(ixmin+1,ixmax): mask[x][ypos]=1.0
            mask[ixmax][ypos]=rxmax
    for ypos in xrange(ranges.shape[0]):
        lastval=ranges[ypos][0]
        for sp in xrange(1,ranges.shape[1]):
            if  ranges[ypos][sp]==0:
                ranges[ypos][sp]=lastval
            lastval=ranges[ypos][sp]
    

    maskedimg=(image.pix*mask.T)
    flux=np.zeros((maskedimg.shape[0],ranges.shape[1]-1))
    for r in xrange(flux.shape[0]):
        row=np.add.reduceat(maskedimg[r],ranges[r])[:-1]
        flux[r]=row

    from desispec.interpolation import resample_flux

    wtarget=np.arange(wmin,wmax+dw/2.0,dw) #- using same wmin and wmax.
    fflux=np.zeros((500,len(wtarget)))
    ivar=np.zeros((500,len(wtarget)))
    resolution=np.zeros((500,21,len(wtarget))) #- placeholder for online case. Offline should be usable
    #TODO get the approximate resolution matrix for online purpose or don't need them? How to perform fiberflat, sky subtraction etc or should have different version of them for online?
    for spec in xrange(flux.shape[1]):
        ww=psf.wavelength(spec)
        fflux[spec,:]=resample_flux(wtarget,ww,flux[:,spec])
        ivar[spec,:]=1./(fflux[spec,:].clip(0.0)+image.readnoise) #- taking only positive pixel counts
    dwave=np.gradient(wtarget)
    fflux/=dwave
    ivar*=dwave**2
    #- Extracted the full image but write frame in [nspec,nwave]
    #- return a desispec.frame object
    return Frame(wtarget,fflux[:nspec],ivar[:nspec],resolution_data=resolution[:nspec],spectrograph=spectrograph)
