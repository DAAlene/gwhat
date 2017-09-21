# -*- coding: utf-8 -*-
"""
Copyright 2014-2017 Jean-Sebastien Gosselin
email: jean-sebastien.gosselin@ete.inrs.ca

This file is part of WHAT (Well Hydrograph Analysis Toolbox).

WHAT is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# Standard library imports :
import os

# Third party imports :
import pandas as pd
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QDialog, QApplication, QGridLayout,
                             QLabel, QPushButton, QCheckBox, QLineEdit,
                             QFileDialog)

# Local imports :

from common import IconDB, QToolButtonSmall
from meteo.weather_reader import read_weather_datafile


def merge_datafiles(datafiles, mode='overwrite'):
    # mode can be either 'overwrite' or 'average'
    global dset1, dset2, dset12

    dset1 = pd.DataFrame.from_dict(datafiles[0])
    dset1.index = dset1.Time

    dset2 = pd.DataFrame.from_dict(datafiles[1])
    dset2.index = dset2.Time

    dset12 = dset1.combine_first(dset2)

#    df['Tmax'] = data[:, var.index('Max Temp (deg C)')]
#    df['Tmin'] = data[:, var.index('Min Temp (deg C)')]
#    df['Tavg'] = data[:, var.index('Mean Temp (deg C)')]
#    df['Ptot'] = data[:, var.index('Total Precip (mm)')]


class WXDataMerger(object):
    """Base class to read and merge input weather datafiles."""

    def __init__(self):

        self.DATA = []        # Weather data
        self.DATE = []        # Date in tuple format [YEAR, MONTH, DAY]
        self.TIME = []        # Date in numeric format

        self.DATE_START = []  # Date on which the data record begins
        self.DATE_END = []    # Date on which data record ends

        self.STANAME = []     # Station names
        self.ALT = []         # Station elevation in m
        self.LAT = []         # Station latitude in decimal degree
        self.LON = []         # Station longitude in decimal degree
        self.VARNAME = []     # Names of the meteorological variables
        self.ClimateID = []   # Climate Identifiers of weather station
        self.PROVINCE = []    # Provinces where weater station are located

        self.NUMMISS = []     # Number of missing data
        self.fnames = []

    def load_and_format_data(self, pathlist):

        nSTA = len(pathlist)  # Number of weather data file
        self.fnames = np.zeros(nSTA).astype(object)
        for i, path in enumerate(pathlist):
            self.fnames[i] = os.path.basename(path)

        if nSTA == 0:  # Reset states of all class variables
            self.STANAME = []
            self.ALT = []
            self.LAT = []
            self.LON = []
            self.PROVINCE = []
            self.ClimateID = []
            self.DATE_START = []
            self.DATE_END = []

            return False

        # Variable Initialization ---------------------------------------------

        self.STANAME = np.zeros(nSTA).astype('str')
        self.ALT = np.zeros(nSTA)
        self.LAT = np.zeros(nSTA)
        self.LON = np.zeros(nSTA)
        self.PROVINCE = np.zeros(nSTA).astype('str')
        self.ClimateID = np.zeros(nSTA).astype('str')
        self.DATE_START = np.zeros((nSTA, 3)).astype('int')
        self.DATE_END = np.zeros((nSTA, 3)).astype('int')

        FLAG_date = False
        # If FLAG_date becomes True, a new DATE matrix will be rebuilt at the
        # end of this routine.

        for i in range(nSTA):

            # ---------------------------------------- WEATHER DATA IMPORT ----

            with open(paths[i], 'r', encoding='utf8') as f:
                reader = list(csv.reader(f, delimiter='\t'))

            STADAT = np.array(reader[8:]).astype(float)

            self.DATE_START[i, :] = STADAT[0, :3]
            self.DATE_END[i, :] = STADAT[-1, :3]

            # -------------------------------------- TIME CONTINUITY CHECK ----

            # Check if data are continuous over time. If not, the serie will be
            # made continuous and the gaps will be filled with nan values.
            print(reader[0][1])

            time_start = xldate_from_date_tuple((STADAT[0, 0].astype('int'),
                                                 STADAT[0, 1].astype('int'),
                                                 STADAT[0, 2].astype('int')),
                                                0)

            time_end = xldate_from_date_tuple((STADAT[-1, 0].astype('int'),
                                               STADAT[-1, 1].astype('int'),
                                               STADAT[-1, 2].astype('int')),
                                              0)

            print(time_start, time_end, len(STADAT[:, 0]))
            print(time_end - time_start + 1)

            if (time_end - time_start + 1) != len(STADAT[:, 0]):
                print('\n%s is not continuous, correcting...' % reader[0][1])
                STADAT = self.make_timeserie_continuous(STADAT)
                print('%s is now continuous.' % reader[0][1])

            # TODO: ajouter un check permettant de reconnaitre quand les
            # donnees ne sont pas exclusivement croissante dans le temps.
            # Ajouter des alertes lorsque il y a un problème.

            time_new = np.arange(time_start, time_end + 1)

            # ----------------------------------------- FIRST TIME ROUTINE ----

            if i == 0:
                self.VARNAME = reader[7][3:]
                nVAR = len(self.VARNAME)  # number of meteorological variable
                self.TIME = np.copy(time_new)
                self.DATA = np.zeros((len(STADAT[:, 0]), nSTA, nVAR)) * np.nan
                self.DATE = STADAT[:, :3]
                self.NUMMISS = np.zeros((nSTA, nVAR)).astype('int')

            # ---------------------------------- <DATA> & <TIME> RESHAPING ----

            # This part of the function fits neighboring data series to the
            # target data serie in the 3D data matrix. Default values in the
            # 3D data matrix are nan.

            if self.TIME[0] <= time_new[0]:
                if self.TIME[-1] >= time_new[-1]:

                    #    [---------------]    self.TIME
                    #         [-----]         time_new

                    pass

                else:

                    #    [--------------]         self.TIME
                    #         [--------------]    time_new
                    #
                    #           OR
                    #
                    #    [--------------]           self.TIME
                    #                     [----]    time_new

                    FLAG_date = True

                    # Expand <DATA> and <TIME> to fit the new data serie

                    EXPND = np.zeros((int(time_new[-1]-self.TIME[-1]),
                                      nSTA,
                                      nVAR)) * np.nan

                    self.DATA = np.vstack((self.DATA, EXPND))
                    self.TIME = np.arange(self.TIME[0], time_new[-1] + 1)

            elif self.TIME[0] > time_new[0]:
                if self.TIME[-1] >= time_new[-1]:

                    #        [----------]    self.TIME
                    #    [----------]        time_new
                    #
                    #            OR
                    #           [----------]    self.TIME
                    #    [----]                 time_new

                    FLAG_date = True

                    # Expand <DATA> and <TIME> to fit the new data serie

                    EXPND = np.zeros((int(self.TIME[0]-time_new[0]),
                                      nSTA,
                                      nVAR)) * np.nan

                    self.DATA = np.vstack((EXPND, self.DATA))
                    self.TIME = np.arange(time_new[0], self.TIME[-1] + 1)
                else:

                    #        [----------]        self.TIME
                    #    [------------------]    time_new

                    FLAG_date = True

                    # Expand <DATA> and <TIME> to fit the new data serie

                    EXPNDbeg = np.zeros((int(self.TIME[0]-time_new[0]),
                                         nSTA,
                                         nVAR)) * np.nan

                    EXPNDend = np.zeros((int(time_new[-1]-self.TIME[-1]),
                                         nSTA,
                                         nVAR)) * np.nan

                    self.DATA = np.vstack((EXPNDbeg, self.DATA, EXPNDend))

                    self.TIME = np.copy(time_new)

            ifirst = np.where(self.TIME == time_new[0])[0][0]
            ilast = np.where(self.TIME == time_new[-1])[0][0]
            self.DATA[ifirst:ilast+1, i, :] = STADAT[:, 3:]

            # --------------------------------------------------- Other Info --

            # Nbr. of Missing Data :

            isnan = np.isnan(STADAT[:, 3:])
            self.NUMMISS[i, :] = np.sum(isnan, axis=0)

            # station name :

            # Check if a station with this name already exist in the list.
            # If so, a number at the end of the name is added so it is
            # possible to differentiate them in the list.

            isNameExist = np.where(reader[0][1] == self.STANAME)[0]
            if len(isNameExist) > 0:

                msg = ('Station name %s already exists. '
                       'Added a number at the end.') % reader[0][1]
                print(msg)

                count = 1
                while len(isNameExist) > 0:
                    newname = '%s (%d)' % (reader[0][1], count)
                    isNameExist = np.where(newname == self.STANAME)[0]
                    count += 1

                self.STANAME[i] = newname

            else:
                self.STANAME[i] = reader[0][1]

            # Other station info :

            self.PROVINCE[i] = str(reader[1][1])
            self.LAT[i] = float(reader[2][1])
            self.LON[i] = float(reader[3][1])
            self.ALT[i] = float(reader[4][1])
            self.ClimateID[i] = str(reader[5][1])

        # ------------------------------------ SORT STATION ALPHABETICALLY ----

        sort_index = np.argsort(self.STANAME)

        self.DATA = self.DATA[:, sort_index, :]
        self.STANAME = self.STANAME[sort_index]
        self.PROVINCE = self.PROVINCE[sort_index]
        self.LAT = self.LAT[sort_index]
        self.LON = self.LON[sort_index]
        self.ALT = self.ALT[sort_index]
        self.ClimateID = self.ClimateID[sort_index]

        self.NUMMISS = self.NUMMISS[sort_index, :]
        self.DATE_START = self.DATE_START[sort_index]
        self.DATE_END = self.DATE_END[sort_index]

        self.fnames = self.fnames[sort_index]

        # -------------------------------------------- GENERATE DATE SERIE ----

        # Rebuild a date matrix if <DATA> size changed. Otherwise, do nothing
        # and keep *Date* as is.

        if FLAG_date is True:
            self.DATE = np.zeros((len(self.TIME), 3))
            for i in range(len(self.TIME)):
                date_tuple = xldate_as_tuple(self.TIME[i], 0)
                self.DATE[i, 0] = date_tuple[0]
                self.DATE[i, 1] = date_tuple[1]
                self.DATE[i, 2] = date_tuple[2]

        return True

    # =========================================================================

    def make_timeserie_continuous(self, DATA):
        # scan the entire time serie and will insert a row with nan values
        # whenever there is a gap in the data and will return the continuous
        # data set.
        #
        # DATA = [YEAR, MONTH, DAY, VAR1, VAR2 ... VARn]
        #
        # 2D matrix containing the dates and the corresponding daily
        # meteorological data of a given weather station arranged in
        # chronological order.

        nVAR = len(DATA[0, :]) - 3  # number of meteorological variables
        nan2insert = np.zeros(nVAR) * np.nan

        i = 0
        date1 = xldate_from_date_tuple((DATA[i, 0].astype('int'),
                                        DATA[i, 1].astype('int'),
                                        DATA[i, 2].astype('int')), 0)

        while i < len(DATA[:, 0]) - 1:
            date2 = xldate_from_date_tuple((DATA[i+1, 0].astype('int'),
                                            DATA[i+1, 1].astype('int'),
                                            DATA[i+1, 2].astype('int')), 0)

            # If dates 1 and 2 are not consecutive, add a nan row to DATA
            # after date 1.
            if date2 - date1 > 1:
                date2insert = np.array(xldate_as_tuple(date1 + 1, 0))[:3]
                row2insert = np.append(date2insert, nan2insert)
                DATA = np.insert(DATA, i + 1, row2insert, 0)

            date1 += 1
            i += 1

        return DATA

    def generate_summary(self, project_folder):  # ============================

        """
        This method generates a summary of the weather records including
        all the data files contained in */<project_folder>/Meteo/Input*,
        including dates when the records begin and end, total number of data,
        and total number of data missing for each meteorological variable, and
        more.
        """

        fcontent = [['#', 'STATION NAMES', 'ClimateID',
                     'Lat. (dd)', 'Lon. (dd)', 'Alt. (m)',
                     'DATE START', 'DATE END', 'Nbr YEARS', 'TOTAL DATA',
                     'MISSING Tmax', 'MISSING Tmin', 'MISSING Tmean',
                     'Missing Precip']]

        for i in range(len(self.STANAME)):
            record_date_start = '%04d/%02d/%02d' % (self.DATE_START[i, 0],
                                                    self.DATE_START[i, 1],
                                                    self.DATE_START[i, 2])

            record_date_end = '%04d/%02d/%02d' % (self.DATE_END[i, 0],
                                                  self.DATE_END[i, 1],
                                                  self.DATE_END[i, 2])

            time_start = xldate_from_date_tuple((self.DATE_START[i, 0],
                                                 self.DATE_START[i, 1],
                                                 self.DATE_START[i, 2]), 0)

            time_end = xldate_from_date_tuple((self.DATE_END[i, 0],
                                               self.DATE_END[i, 1],
                                               self.DATE_END[i, 2]), 0)

            number_data = float(time_end - time_start + 1)

            fcontent.append([i+1, self.STANAME[i],
                             self.ClimateID[i],
                             '%0.2f' % self.LAT[i],
                             '%0.2f' % self.LON[i],
                             '%0.2f' % self.ALT[i],
                             record_date_start,
                             record_date_end,
                             '%0.1f' % (number_data / 365.25),
                             number_data])

            # Missing data information for each meteorological variables
            for var in range(len(self.VARNAME)):
                fcontent[-1].extend(['%d' % (self.NUMMISS[i, var])])

#                txt1 = self.NUMMISS[i, var]
#                txt2 = self.NUMMISS[i, var] / number_data * 100
#                CONTENT[-1].extend(['%d (%0.1f %%)' % (txt1, txt2)])

#            # Total missing data information.
#            txt1 = np.sum(self.NUMMISS[i, :])
#            txt2 = txt1 / (number_data * nVAR) * 100
#            CONTENT[-1].extend(['%d (%0.1f %%)' % (txt1, txt2)])

        output_path = project_folder + '/weather_datasets_summary.log'

        with open(output_path, 'w') as f:
            writer = csv.writer(f, delimiter='\t', lineterminator='\n')
            writer.writerows(fcontent)

    def read_summary(self, project_folder):  # ================================

        """
        This method read the content of the file generated by the method
        <generate_summary> and will return the content of the file in a HTML
        formatted table
        """

        # ------------------------------------------------------ read data ----

        filename = project_folder + '/weather_datasets_summary.log'
        with open(filename, 'r') as f:
            reader = list(csv.reader(f, delimiter='\t'))
            reader = reader[1:]

#        FIELDS = ['&#916;Alt.<br>(m)', 'Dist.<br>(km)', 'Tmax',
#                  'Tmin', 'Tmean', 'Ptot']

        # ----------------------------------------- generate table summary ----

        table = '''
                <table border="0" cellpadding="3" cellspacing="0"
                 align="center">
                  <tr>
                    <td colspan="10"><hr></td>
                  </tr>
                  <tr>
                    <td align="center" valign="bottom"  width=30 rowspan="3">
                      #
                    </td>
                    <td align="left" valign="bottom" rowspan="3">
                      Station
                    </td>
                    <td align="center" valign="bottom" rowspan="3">
                      Climate<br>ID
                    </td>
                    <td align="center" valign="bottom" rowspan="3">
                      From<br>year
                    </td>
                    <td align="center" valign="bottom" rowspan="3">
                      To<br>year
                    </td>
                    <td align="center" valign="bottom" rowspan="3">
                      Nbr.<br>of<br>years
                    <td align="center" valign="middle" colspan="4">
                      % of missing data for
                    </td>
                  </tr>
                  <tr>
                    <td colspan="4"><hr></td>
                  </tr>
                  <tr>
                    <td align="center" valign="middle">
                      T<sub>max</sub>
                    </td>
                    <td align="center" valign="middle">
                      T<sub>min</sub>
                    </td>
                    <td align="center" valign="middle">
                      T<sub>mean</sub>
                    </td>
                    <td align="center" valign="middle">
                      P<sub>tot</sub>
                    </td>
                  </tr>
                  <tr>
                    <td colspan="10"><hr></td>
                  </tr>
                '''
        for i in range(len(reader)):

            color = ['transparent', '#E6E6E6']

            Ntotal = float(reader[i][9])
            TMAX = float(reader[i][10]) / Ntotal * 100
            TMIN = float(reader[i][11]) / Ntotal * 100
            TMEAN = float(reader[i][12]) / Ntotal * 100
            PTOT = float(reader[i][13]) / Ntotal * 100
            firstyear = reader[i][6][:4]
            lastyear = reader[i][7][:4]
            nyears = float(lastyear) - float(firstyear)

            table += '''
                     <tr bgcolor="%s">
                       <td align="center" valign="middle">
                         %02d
                       </td>
                       <td align="left" valign="middle">
                         <font size="3">%s</font>
                       </td>
                       <td align="center" valign="middle">
                         <font size="3">%s</font>
                       </td>
                       <td align="center" valign="middle">
                         <font size="3">%s</font>
                       </td>
                       <td align="center" valign="middle">
                         <font size="3">%s</font>
                       </td>
                       <td align="center" valign="middle">
                         <font size="3">%0.0f</font>
                       </td>
                       <td align="center" valign="middle">%0.0f</td>
                       <td align="center" valign="middle">%0.0f</td>
                       <td align="center" valign="middle">%0.0f</td>
                       <td align="center" valign="middle">%0.0f</td>
                     </tr>
                     ''' % (color[i % 2], i+1, reader[i][1], reader[i][2],
                            firstyear, lastyear, nyears,
                            TMAX, TMIN, TMEAN, PTOT)

        table += """
                   <tr>
                     <td colspan="10"><hr></td>
                   </tr>
                 </table>
                 """

        return table



class WXDataMergerWidget(QDialog):

    def __init__(self, wxdset=None, parent=None):
        super(WXDataMergerWidget, self).__init__(parent)

        self.setModal(False)
        self.setWindowFlags(Qt.CustomizeWindowHint |
                            Qt.WindowCloseButtonHint)

        self.setWindowTitle('Merge dataset')
        self.setWindowIcon(IconDB().master)
        self._workdir = os.getcwd()
        self.wxdsets = {}

        self.__initUI__()

    def __initUI__(self):

        # ---- Toolbar ----

        btn_merge = QPushButton('Merge')
        btn_merge.clicked.connect(self.btn_merge_isClicked)
        btn_cancel = QPushButton('Close')
        btn_cancel.clicked.connect(self.close)

        toolbar = QGridLayout()
        toolbar.addWidget(btn_merge, 0, 1)
        toolbar.addWidget(btn_cancel, 0, 2)
        toolbar.setColumnStretch(0, 100)
        toolbar.setContentsMargins(0, 25, 0, 0)  # (L, T, R, B)

        # ---- Central Widget ----

        self._file_path1 = QLineEdit()
        self._file_path1.setReadOnly(True)
        lbl_get_file1 = QLabel("Select a first dataset :")
        btn_get_file1 = QToolButtonSmall(IconDB().openFile)
        btn_get_file1.file_path = self._file_path1
        btn_get_file1.clicked.connect(self.set_first_filepath)

        self._file_path2 = QLineEdit()
        self._file_path2.setReadOnly(True)
        lbl_get_file2 = QLabel("Select a second dataset :")
        btn_get_file2 = QToolButtonSmall(IconDB().openFile)
        btn_get_file2.file_path = self._file_path2
        btn_get_file2.clicked.connect(self.set_second_filepath)

        lbl_wxdset3 = QLabel("Enter a name for the resulting dataset :")
        wxdset3 = QLineEdit()

        qchckbox = QCheckBox(
                "Delete both original input datafiles after merging.")
        qchckbox.setCheckState(Qt.Checked)

        # ---- Setup Layout ----

        # Place widgets for file #1.
        central_layout = QGridLayout()
        row = 0
        central_layout.addWidget(lbl_get_file1, row, 0, 1, 2)
        row += 1
        central_layout.addWidget(self._file_path1, row, 0)
        central_layout.addWidget(btn_get_file1, row, 1)
        row += 1
        central_layout.setRowMinimumHeight(row, 15)
        row += 1
        # Place widgets for file #2.
        central_layout.addWidget(lbl_get_file2, row, 0, 1, 2)
        row += 1
        central_layout.addWidget(self._file_path2, row, 0)
        central_layout.addWidget(btn_get_file2, row, 1)
        row += 1
        central_layout.setRowMinimumHeight(row, 15)
        row += 1
        # Place widgets for concatenated file.
        central_layout.addWidget(lbl_wxdset3, row, 0, 1, 2)
        row += 1
        central_layout.addWidget(wxdset3, row, 0, 1, 2)
        row += 1
        central_layout.setRowMinimumHeight(row, 15)
        row += 1
        central_layout.addWidget(qchckbox, row, 0, 1, 2)
        central_layout.setColumnStretch(1, 100)

        # ---- Self Layout ----

        layout = QGridLayout(self)
        layout.addLayout(central_layout, 0, 0)
        layout.addLayout(toolbar, 1, 0)

    def set_first_filepath(self, fpath=None):
        if fpath is None:
            fpath = self.get_filepath()
        if fpath:
            self._file_path1.setText(fpath)
            self.wxdsets['file1'] = read_weather_datafile(fpath)

    def set_second_filepath(self, fpath=None):
        if fpath is None:
            fpath = self.get_filepath()
        if fpath:
            self._file_path2.setText(fpath)
            self.wxdsets['file2'] = read_weather_datafile(fpath)

    def get_filepath(self):
        fpath, ftype = QFileDialog.getOpenFileName(
                self, 'Select a valid weather data file', self._workdir,
                '*.csv')
        return fpath

    def set_workdir(self, dirname):
        if os.path.exists(dirname):
            self._workdir = dirname

    def btn_merge_isClicked(self):
        if len(self.wxdsets) >= 2:
            merge_datafiles(list(self.wxdsets.values()))
        self.close()

    def show(self):
        super(WXDataMergerWidget, self).show()
        self.setFixedSize(self.size())


if __name__ == '__main__':                                   # pragma: no cover
    import platform
    import sys

    app = QApplication(sys.argv)

    if platform.system() == 'Windows':
        app.setFont(QFont('Segoe UI', 11))
    elif platform.system() == 'Linux':
        app.setFont(QFont('Ubuntu', 11))

    wxdata_merger = WXDataMergerWidget()

    workdir = os.path.join("..", "tests", "@ new-prô'jèt!", "Meteo", "Input")
    wxdata_merger.set_workdir(workdir)

    file1 = os.path.join(workdir, "IBERVILLE (7023270)_2000-2010.csv")
    file2 = os.path.join(workdir, "L'ACADIE (702LED4)_2000-2010.csv")

    wxdata_merger.set_first_filepath(file1)
    wxdata_merger.set_second_filepath(file1)
    wxdata_merger.show()

    sys.exit(app.exec_())
