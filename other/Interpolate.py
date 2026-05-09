from scipy.interpolate import interp1d


def interpolate(x_list, y_list, x_, interp_type='linear'):
    # interp_type can be linear, cubic, soline, etc.
    
    x = np.asarray(x_list)
    y = np.asarray(y_list)
    
    if interp_type == 'exponential':
        if np.any(y <= 0):
            raise ValueError("Exponential interpolation requires all y > 0")

        f = interp1d(x, np.log(y), kind='linear', fill_value="extrapolate")
        return np.exp(f(x_))
        
    else:
        f = interp1d(x, y, kind=interp_type, fill_value="extrapolate")
        return f(x_)


