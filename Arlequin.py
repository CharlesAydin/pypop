#! /usr/bin/env python

"""Module for exposing Arlequin functionality in Python.

"""
import sys, string, os, re, shutil

class ArlequinBatch:
    """A Python `wrapper' class for Arlequin.
    
    Given a delimited text file of multi-locus genotype data: provides
    methods to output Arlequin format data files and runtime info and
    execution of Arlequin itself.

    Is used to provide a `batch' (command line) mode for generating
    appropriate Arlequin input files and for forking Arlequin
    itself."""
    
    def __init__(self,
                 arpFilename,
                 arsFilename,
                 idCol,
                 prefixCols,
                 suffixCols,
                 windowSize,
                 untypedAllele = '0',
                 arlequinPrefix = "arl_run",
                 debug=0):

        """Constructor for HaploArlequin object.

        Expects:

        - arpFilename: Arlequin filename (must have '.arp' file
          extension)

        - arsFilename: Arlequin settings filename (must have '.ars' file
          extension)

        - idCol: column in input file that contains the individual id.
        
        - prefixCols: number of columns to ignore before allele data
          starts
        
        - suffixCols: number of columns to ignore after allele data
          stops
        
        - windowSize: size of sliding window
        
        - untypedAllele:  (defaults to '0')
        
        - arlequinPrefix: prefix for all Arlequin run-time files
        (defaults to 'arl_run').

        - debug: (defaults to 0)
        
        """
        self.arpFilename = arpFilename
        self.arsFilename = arsFilename
        self.idCol = idCol
        self.prefixCols = prefixCols
        self.suffixCols = suffixCols
        self.windowSize = windowSize
        self.arlequinPrefix = arlequinPrefix
        self.untypedAllele = untypedAllele
        self.debug = debug

        if arpFilename[-4:] == '.arp':
            self.arpFilename = arpFilename
            self.arlResPrefix = arpFilename[:-4]
        else:
            sys.exit("Error: Arlequin filename: %s does not have a .arp suffix", arpFilename)
        if arsFilename[-4:] == '.ars':
            self.arsFilename = arsFilename
        else:
            sys.exit("Error: Arlequin settings filename: %s does not have a .ars suffix", arpFilename)
            
    def _outputHeader(self, sampleCount):

        headerLines = []
        headerLines.append("""[Profile]
        
        Title=\"Arlequin sample run\"
        NbSamples=%d

             GenotypicData=1
             GameticPhase=0
             DataType=STANDARD
             LocusSeparator=WHITESPACE
             MissingData='%s'
             RecessiveData=0                         
             RecessiveAllele=\"null\" """ % (sampleCount, self.untypedAllele))

        headerLines.append("""[Data]

        [[Samples]]""")

        return headerLines

    def _outputSample (self, data, startCol, endCol):

        # store output Arlequin-formatted genotypes in an array
        samples = []
        sampleLines = []
        
        # convert columns to locus number
        startLocus = (startCol - self.prefixCols)/2 + 1
        endLocus = (startLocus - 1) + (endCol - startCol)/2

        chunk = xrange(startCol, endCol)
        for line in data:
            words = string.split(line)
            unphase1 = "%10s 1 " % words[self.idCol]
            unphase2 = "%13s" % " "
            for i in chunk:
                allele = words[i]
                # don't output individual if *any* loci is untyped
                if allele == self.untypedAllele:
                    if self.debug:
                        print "untyped allele %s in (%s), (%s)" \
                              % (allele, unphase1, unphase2)
                    break
                if ((i - startCol) % 2): unphase1 = unphase1 + " " + allele
                else: unphase2 = unphase2 + " " + allele
            else:
                # store formatted output samples
                samples.append(unphase1 + os.linesep)
                samples.append(unphase2 + os.linesep)

        # adjust the output count of samples for the `SamplesSize'
        # metadata field

        if len(samples) != 0:
            sampleLines.append("""
            
            SampleName=\"%s pop with %s individuals from locus %d to %d\"
            SampleSize= %s
            SampleData={"""  % (self.arlResPrefix, len(samples)/2, startLocus, endLocus, len(samples)/2))

            sampleLines.append(os.linesep)

            # output previously-stored samples to stream only after
            # calculation of number of samples is made
            for line in samples:
                sampleLines.append(line)
            sampleLines.append("}")
            validSample = 1
        else:
            validSample = 0

        return sampleLines, validSample

    def outputArlequin(self, data):
        """Outputs the specified .arp sample file.
        """
        
        if self.debug:
            print "Counted", len(data), "lines."
        firstLine = data[0]

        # calculate the number of loci from the number of columns
        # and the prefix and suffix columns which can be ignored  
        cols = len(string.split(firstLine))
        colCount = cols - (self.prefixCols + self.suffixCols)

        # sanity check to ensure column number is even (2 alleles for
        # each loci)
        if colCount % 2 != 0:
            sys.exit ("Error: col count (%d) is not even" % colCount)
        else:
            locusCount = (colCount)/2

        if self.debug:
            print "First line", firstLine, "has", cols, "columns and", \
                  locusCount, "allele pairs"

        # if windowSize is set to zero, the default to using
        # locusCount as windowSize

        if self.windowSize == 0:
            self.windowSize = locusCount

        chunk = xrange(0, locusCount - self.windowSize + 1)

        sampleCount = 0
        totalSamples = []
        
        for locus in chunk:
            start = self.prefixCols + locus*2
            end = start + self.windowSize*2
            sampleLines, validSample = self._outputSample(data, start, end)
            totalSamples.extend(sampleLines)
            sampleCount += validSample

        headerLines = self._outputHeader(sampleCount)

        if self.debug:
            print "sample count", sampleCount
            
        # open specified arp
        self.arpFile = open(self.arpFilename, 'w')
        for line in headerLines:
            self.arpFile.write(line)
        for line in totalSamples:
            self.arpFile.write(line)
        # close .arp file
        self.arpFile.close()

    def _outputArlRunTxt(self, txtFilename, arpFilename):
        """Outputs the run-time Arlequin program file.
        """
        file = open(txtFilename, 'w')
        file.write("""%s
use_interf_settings
%s%s%s
0
0
end""" % (os.getcwd(), os.getcwd(), os.sep, arpFilename))

    def _outputArlRunArs(self, systemArsFilename, arsFilename):
        """Outputs the run-time Arlequin program file.
        """
        shutil.copy(arsFilename, systemArsFilename)

    def outputRunFiles(self):
        """Generates the expected '.txt' set-up files for Arlequin.
        """
        self._outputArlRunTxt(self.arlequinPrefix + ".txt", self.arpFilename)
        self._outputArlRunArs(self.arlequinPrefix + ".ars", self.arsFilename)
    
    def runArlequin(self):
        """Run the Arlequin haplotyping program.
         
        Forks a copy of 'arlecore.exe', which must be on 'PATH' to
        actually generate the desired statistics estimates from the
        generated '.arp' file.  """

        # spawn external Arlequin process
        os.system("arlecore.exe")

        # fix permissions on result directory because Arlequin is
        # brain-dead with respect to file permissions on Unix
        os.chmod(self.arlResPrefix + ".res", 0755)

# this is called if this module is executed standalone
if __name__ == "__main__":

    usage_message = """Usage: Arlequin.py [OPTION] INPUTFILE ARPFILE ARSFILE
Process a tab-delimited INPUTFILE of alleles to produce an data files
(including ARPFILE), using parameters from ARSFILE for the Arlequin population
genetics program.

 -i, --idcol=NUM       column number of identifier (first column is zero)
 -k, --cols=POS1,POS2  number of leading columns (POS1) before start and end
                        (POS2) of allele data (including IDCOL)
 -w, --windowsize=NUM  number of loci involved in window size 
                        (note that this is twice the number of allele columns)
 -x, --execute         execute the Arlequin program
 -h, --help            this message
 -d, --debug           switch on debugging

  INPUTFILE   input text file
  ARPFILE     output Arlequin '.arp' project file
  ARSFILE     input Arlequin '.ars' settings file"""

    from getopt import getopt, GetoptError

    try: opts, args = \
         getopt(sys.argv[1:],"i:k:w:xhd",\
                ["idcol", "cols", "windowsize", "help", "execute", "debug"])
    except GetoptError:
        sys.exit(usage_message)

    # default options
    idCol = 0
    prefixCols = 1
    suffixCols = 0
    windowSize = 0
    executeFlag = 0
    debug = 0

    # parse options
    for o, v in opts:
        if o in ("-i", "--idcol"):
            idCol = int(v)
        elif o in ("-k", "--cols"):
            prefixCols, suffixCols = map(int, string.split(v, ','))
        elif o in ("-t", "--trailcols"):
            suffixCols = int(v)
        elif o in ("-w", "--windowsize"):
            windowSize = int(v)
        elif o in ("-h", "--help"):
            sys.exit(usage_message)
        elif o in ("-x", "--execute"):
            executeFlag = 1
        elif o in ("-d", "--debug"):
            debug = 1

    # check number of arguments
    if len(args) != 3:
        sys.exit(usage_message)

    # parse arguments
    inputFilename = args[0]
    arpFilename = args[1]
    arsFilename = args[2]
    
    batch = ArlequinBatch(arpFilename = arpFilename,
                               arsFilename = arsFilename,
                               idCol = idCol,
                               prefixCols = prefixCols,
                               suffixCols = suffixCols,
                               windowSize = windowSize,
                               debug=debug)
    batch.outputArlequin(open(inputFilename, 'r').readlines())
    batch.outputRunFiles()

    # run Arlequin if asked
    if executeFlag:
        batch.runArlequin()