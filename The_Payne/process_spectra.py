'''
Code for reading in combined spectra.
This uses Jo Bovy's APOGEE package to read in spectra: https://github.com/jobovy/apogee
Any way that you can get your hands on the spectra should be fine, as long as you 

Here we adopt APOGEE DR14. Edit os.environs below for a later version of APOGEE data release.
Since our spectral model training set was normalized using the DR12 wavelength definition, 
even thought the spectra are from DR14, we will resample them into DR12 wavelength format.
'''

from __future__ import absolute_import, division, print_function # python2 compatibility
import numpy as np
import sys
import os
import subprocess
import astropy.io.fits as pyfits
    
from . import utils
from . import spectral_model

# dr14
master_path = "data.sdss3.org/sas/dr14/apogee/spectro/redux/r8/stars/" 
catalog_path = "l31c/l31c.2/"
catalog_name = "allStar-l31c.2.fits"

# download path
download_path = "apogee_download/"

os.environ["SDSS_LOCAL_SAS_MIRROR"] = "data.sdss3.org/sas/"
os.environ["RESULTS_VERS"] = "l31c.2" #v603 for DR12, l30e.2 for DR13, l31c.2 for DR14
os.environ["APOGEE_APOKASC_REDUX"] = "v6.2a"

from apogee.tools import toAspcapGrid


# read in the list of pixels used for fitting the APOGEE continuum
cont_pixels = utils.load_cannon_contpixels()

def read_apogee_catalog():
    '''
    read in the catalog of info for all stars in a data release. 
    '''
    filepath = os.path.join(master_path, catalog_path, catalog_name)  # dr14
    filename = os.path.join(download_path, catalog_name)
    
    #try:
    print(download_path)
    os.makedirs(os.path.dirname(download_path))
    #except OSError: pass
    if not os.path.exists(filename):
        subprocess.check_call(["wget", filepath, "-O", "%s"%filename])

    all_star_catalog = pyfits.getdata(filename)
    catalog_id = all_star_catalog['APOGEE_ID'].astype("str")
    return all_star_catalog, catalog_id



def get_combined_spectrum_single_object(apogee_id, catalog = None, save_local = False):
    '''
    apogee_id should be a byte-like object; i.e b'2M13012770+5754582'
    This downloads a single combined spectrum and the associated error array,
        and it normalizes both. 
    '''
    
    # read in the allStar catalog if you haven't already
    if catalog is None:
        catalog, catalog_id = read_apogee_catalog()
    
    _COMBINED_INDEX = 1
    
    msk = np.where(catalog_id == apogee_id)[0]
    if not len(msk):
        raise ValueError('the desired Apogee ID was not found in the allStar catalog.')

    field = catalog['FIELD'][msk[0]]
    loc_id = catalog['LOCATION_ID'][msk[0]]

    filename = 'apStar-r8-%s.fits' % apogee_id.strip()
    if loc_id == 1:
        filepath = os.path.join(master_path,'apo1m', field.strip(), filename)
    else:
        filepath = os.path.join(master_path,'apo25m', '%i' % loc_id, filename)
    filename = os.path.join(download_path, filename)
    
    try:
        os.makedirs(os.path.dirname(download_path))
    except OSError: pass
    if not os.path.exists(filename):
        subprocess.check_call(["wget", filepath, '-O', '%s'%filename])

    temp1 = pyfits.getdata(filename, ext = 1, header = False)
    temp2 = pyfits.getdata(filename, ext = 1, header = False)
    temp3 = pyfits.getdata(filename, ext = 1, header = False)
    
    if temp1.shape[0] > 6000:
        spec = temp1
        specerr = temp2
        mask = temp3
    else:
        spec = temp1[_COMBINED_INDEX]
        specerr = temp2[_COMBINED_INDEX]
        mask = temp3[_COMBINED_INDEX]

    spec = toAspcapGrid(spec, dr='12') # dr12 wavelength format
    specerr = toAspcapGrid(specerr, dr='12')
    
    # cull dead pixels
    choose = spec <= 0
    spec[choose] = 0.01
    specerr[choose] = np.max(np.abs(spec))*999.
        
    # continuum-normalize
    cont = utils.get_apogee_continuum(spec = spec, 
        spec_err = specerr, cont_pixels = cont_pixels)
    spec /= cont
    specerr /= cont
    
    if save_local:
        np.savez('spectra/combined/spectrum_ap_id_' + str(apogee_id.decode()) + '_.npz',
                 spectrum = spec, spec_err = specerr)
    return spec, specerr
    

