
from scipy import interpolate
from numpy import zeros
from numpy.linalg import inv
from numpy import dot, linspace, argmax, argmin

def find_critical(R, Z, psi):
    """
    Find critical points

    Inputs
    ------
    
    R - R(nr, nz) 2D array of major radii
    Z - Z(nr, nz) 2D array of heights
    psi - psi(nr, nz) 2D array of psi values

    Returns
    -------
    
    Two lists of critical points

    opoint, xpoint

    Each of these is a list of tuples with (R, Z, psi) points

    The first tuple is the primary O-point (magnetic axis)
    and primary X-point (separatrix)
    
    """

    # Get a spline interpolation function
    f = interpolate.RectBivariateSpline(R[:,0], Z[0,:], psi)

    # Find candidate locations, based on minimising Bp^2
    Bp2 = (f(R,Z,dx=1,grid=False)**2 + f(R,Z,dy=1,grid=False)**2) / R
    
    # Find local minima

    J = zeros([2,2])

    xpoint = []
    opoint = []
    
    nx,ny = Bp2.shape
    for i in range(2,nx-2):
        for j in range(2,ny-2):
            if ( (Bp2[i,j] < Bp2[i+1,j+1])
                 and (Bp2[i,j] < Bp2[i+1,j])
                 and (Bp2[i,j] < Bp2[i+1,j-1])
                 and (Bp2[i,j] < Bp2[i-1,j+1])
                 and (Bp2[i,j] < Bp2[i-1,j])
                 and (Bp2[i,j] < Bp2[i-1,j-1])
                 and (Bp2[i,j] < Bp2[i,j+1])
                 and (Bp2[i,j] < Bp2[i,j-1]) ):

                # Found local minimum

                R0 = R[i,j]
                Z0 = Z[i,j]
                
                # Use Newton iterations to find where
                # both Br and Bz vanish
                R1 = R0
                Z1 = Z0

                count = 0
                while True:
                
                    Br = -f(R1, Z1, dy=1)[0][0]/R1
                    Bz = f(R1, Z1, dx=1)[0][0]/R1

                    if Br**2 + Bz**2 < 1e-6:
                        # Found a minimum. Classify as either
                        # O-point or X-point

                        # Evaluate D = fxx * fyy - (fxy)^2
                        D = f(R1, Z1, dx=2)[0][0] * f(R1, Z1, dy=2)[0][0] - (f(R1, Z1, dx=1, dy=1)[0][0])**2

                        if D < 0.0:
                            # Found X-point
                            xpoint.append( (R1,Z1, f(R1,Z1)[0][0]) )
                        else:
                            # Found O-point
                            opoint.append( (R1,Z1, f(R1,Z1)[0][0]) )
                        break
                        
                    # Jacobian matrix
                    # J = ( dBr/dR, dBr/dZ )
                    #     ( dBz/dR, dBz/dZ )
                
                    J[0,0] = -Br/R1 - f(R1, Z1, dy=1,dx=1)[0][0]/R1
                    J[0,1] = -f(R1, Z1, dy=2)[0][0]/R1
                    J[1,0] = -Bz/R1 + f(R1, Z1, dx=2)/R1
                    J[1,1] = f(R1, Z1, dx=1,dy=1)[0][0]/R1
                
                    d = dot(inv(J), [Br,Bz])

                    R1 = R1 - d[0]
                    Z1 = Z1 - d[1]
                    
                    count += 1
                    # If (R1,Z1) is too far from (R0,Z0) then discard
                    # or if we've taken too many iterations
                    if ((R1 - R0)**2 + (Z1 - Z0)**2 > 1e-2) or (count > 100):
                        # Discard this point
                        break
    

    # Remove duplicates
    def remove_dup(points):
        result = []
        for n, p in enumerate(points):
            dup = False
            for p2 in result:
                if (p[0] - p2[0])**2 + (p[1] - p2[1])**2 < 1e-5:
                    dup = True # Duplicate
                    break
            if not dup:
                result.append(p) # Add to the list
        return result

    xpoint = remove_dup(xpoint)
    opoint = remove_dup(opoint)
    
    if len(opoint) == 0:
        # Can't order primary O-point, X-point so return
        print("Warning: No O points found")
        return opoint, xpoint
    
    # Find primary O-point by sorting by distance from middle of domain
    Rmid = 0.5*(R[-1,0] - R[0,0])
    Zmid = 0.5*(Z[0,-1] - Z[0,0])
    opoint.sort(key=lambda x: (x[0] - Rmid)**2 + (x[1] - Zmid)**2)

    # Draw a line from the O-point to each X-point. Psi should be
    # monotonic; discard those which are not

    Ro,Zo,Po = opoint[0] # The primary O-point
    xpt_keep = []
    for xpt in xpoint:
        Rx, Zx, Px = xpt
        
        rline = linspace(Ro, Rx, num=50)
        zline = linspace(Zo, Zx, num=50)
        
        pline = f(rline, zline, grid=False)

        if Px < Po:
            pline *= -1.0 # Reverse, so pline is maximum at X-point
        
        # Now check that pline is monotonic
        ind = argmax(pline)  # Should be at X-point
        if (rline[ind] - Rx)**2 + (zline[ind] - Zx)**2 > 1e-4:
            # Too far, discard
            continue
        ind = argmin(pline)  # Should be at O-point
        if (rline[ind] - Ro)**2 + (zline[ind] - Zo)**2 > 1e-4:
            # Too far, discard
            continue
        xpt_keep.append(xpt)

    xpoint = xpt_keep

    # Sort X-points by distance to primary O-point in psi space

    psi_axis = opoint[0][2]
    xpoint.sort(key=lambda x: (x[2] - psi_axis)**2)
    psi_bndry = xpoint[0][2]
    
    
    import matplotlib.pyplot as plt
    from plotting import plotEquilibrium
    ax = plotEquilibrium(R, Z, psi)

    for r,z,_ in xpt_keep:
        ax.plot(r,z,'ro')
    for r,z,_ in opoint:
        ax.plot(r,z,'go')

    sep_contour=ax.contour(R,Z,psi, levels=[psi_bndry], colors='r')
    
    plt.show()

    return opoint, xpoint