"""
Collection of CP2K output file readers.
"""

class CP2KBaseReader(object):
    def __init__(self):
        self._results = {}

    @property
    def data(self):
        """
        Returns the parsed data as dictionary
        """
        return self._results


class CP2KOutputFileReader(CP2KBaseReader):
    """
    Parse the CP2K output log file
    """

    def __init__(self, filename):
        super(CP2KOutputFileReader, self).__init__()
        from os import stat

        if stat(filename).st_size == 0:
            raise RuntimeError("CP2K output log file is empty")

        self._fn = filename

    def parse(self):
        """
        TODO: dummy function
        """
        with open (self._fn, 'r') as f:
            output_file_lines = f.readlines()

        for line in output_file_lines:
            if ('ENERGY|' in line):
                self._results['energy']=line.split()[8]



class CP2KEnergyFileReader(CP2KBaseReader):
    """
    Parse the .ener file written by CP2K
    """

    def __init__(self, filename):
        super(CP2KEnergyFileReader, self).__init__()
        self._fh = file(filename, 'r')

    def parse(self):
        """
        Parses the file specified in the initialization
        """
        from scipy.stats import linregress
        from numpy import sum, mean

        txt = self._fh.read()

        # read the energy file:
        data = [map(float, line.split()) for line in txt.split('\n')[1:-1]]
        steps, times, ekin, temp, epot, consqty, usedtime = zip(*data)

        # steps are integers
        steps = map(int, steps)

        self._results = {}

        for key, var in [('kin_E', ekin),
                ('temperature', temp),
                ('pot_E', epot),
                ('conserved_Q', consqty)]:
            self._results[key] = {}
            slope, intercept, r_value, p_value, std_err = linregress(times, var)
            self._results[key]['slope'] = slope
            self._results[key]['intercept'] = intercept
            self._results[key]['r_value'] = r_value
            self._results[key]['p_value'] = p_value
            self._results[key]['std_err'] = std_err

        self._results['total_time'] = sum(usedtime)
        self._results['time_p_timestep'] = mean(usedtime)


class CP2KTrajectoryFileReader(CP2KBaseReader):
    """
    Parse the .traj file written by CP2K
    """

    def __init__(self, filename, timestep):
        super(CP2KTrajectoryFileReader, self).__init__()
        self._fh = file(filename, 'r')
        self._timestep = timestep

    def parse(self):
        """
        Parses the file specified in the initialization
        """
        import re
        import mmap
        from numpy import array, sum, mean

        pos_regex = re.compile(r"""
        (?P<sym>[a-zA-Z0-9]+)\s+
        (?P<x>[-]?\d+[\.]?\d+([E | e][+|-]?\+)?)\s+
        (?P<y>[-]?\d+[\.]?\d+([E | e][+|-]?\+)?)\s+
        (?P<z>[-]?\d+[\.]?\d+([E | e][+|-]?\+)?)""", re.X)

        pos_block_regex = re.compile(r"""
                    # First line contains an integer, and only an integer, the number of atoms
                    ^[ \t]* (?P<natoms> [0-9]+) [ \t]*[\n]  #End first line
                    (?P<comment>.*) [\n] #The second line is ignored
                    (
                        
                        \s*   #White space in the beginning (maybe)
                        [A-Za-z0-9]+  #A tag for a species
                        (
                           \s+ # White space in front of the number
                           [\- | \+ ]? # plus or minus in front of the number (optional)
                            (\d*  #optional decimal in the beginning .0001 is ok, for example
                            [\.]?  #optional dot, 232 is ok
                            \d+)    #optional decimal after the point
                            |  #OR
                            (\d+  #optional decimal in the beginning .0001 is ok, for example
                            [\.]?  #optional dot, 232 is ok
                            \d*)
                            ([E | e][+|-]?\d+)?  # optional E+03, e-05 
                        ){3}                     #  I expect three float values and a tag in front of them
                        .*                       # After the line I do not really care what's  going on, there can be comments or anything
                        [\n]                     # line break at the end
                    )+ #A block should be one or more lines
                    """, re.X | re.M)

        txt = mmap.mmap(self._fh.fileno(), 0, prot=mmap.PROT_READ)
        timestep_in_fs = self._timestep

        #~ traj_arr =  np.array([[[float(pos) for pos in line.split()[1:4] if line]
                                    #~ for line in block.group(0).split('\n')[:-1] if block]
                                        #~ for block in pos_regex.finditer(traj_txt)])
        blocks = [block for block in pos_block_regex.finditer(txt)]

        #~ print txt[:10000]
        #~ print '############'


        #~ print pos_block_regex_2.search(txt).group(0)

        #~ print len(blocks)
        #~ print txt
        traj = array([[[float(match.group('x')), float(match.group('y')), float(match.group('z'))]
                for  match in pos_regex.finditer(block.group(0))]
                    for block in blocks])

        self._results['content'] = {
                'array': traj,
                'timestep_in_fs':timestep_in_fs}
