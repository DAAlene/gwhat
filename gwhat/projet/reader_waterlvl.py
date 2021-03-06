# -*- coding: utf-8 -*-

# Copyright © 2014-2018 GWHAT Project Contributors
# https://github.com/jnsebgosselin/gwhat
#
# This file is part of GWHAT (Ground-Water Hydrograph Analysis Toolbox).
# Licensed under the terms of the GNU General Public License.


# ---- Standard library imports
from copy import deepcopy
import re
import os
import os.path as osp
import csv
from collections import OrderedDict
from collections.abc import Mapping

# ---- Third party imports
import numpy as np
import pandas as pd
import xlrd
from xlrd.xldate import xldate_from_datetime_tuple
from xlrd import xldate_as_tuple

# ---- Local library imports
from gwhat.common.utils import save_content_to_csv

FILE_EXTS = ['.csv', '.xls', '.xlsx']


# ---- Read and Load Water Level Datafiles
INDEX = 'Time'

COL_REGEX = OrderedDict([
    (INDEX, r'(date|time|datetime)'),
    ('BP', r'(bp|baro|patm)'),
    ('WL', r'(wl|waterlevels)'),
    ('ET', r'(et|earthtides)')
    ])
COLUMNS = list(COL_REGEX.keys())

HEADER = {'Well': '', 'Well ID': '',
          'Province': '', 'Municipality': '',
          'Latitude': 0, 'Longitude': 0, 'Elevation': 0}
HEADER_REGEX = {
    'Well': r'(?<!\S)(wellname|name)(:|=)?(?!\S)',
    'Well ID': r'(?<!\S)(wellid|id)(:|=)?(?!\S)',
    'Province': r'(?<!\S)(province|prov)(:|=)?(?!\S)',
    'Municipality': r'(?<!\S)municipality(:|=)?(?!\S)',
    'Latitude': r'(?<!\S)(latitude|lat)(:|=)?(?!\S)',
    'Longitude': r'(?<!\S)(longitude|lon)(:|=)?(?!\S)',
    'Elevation': r'(?<!\S)(elevation|elev|altitude|alt)(:|=)?(?!\S)'
    }


class EmptyWLDataset(pd.DataFrame):
    def __init__(self):
        super().__init__(np.empty((0, len(COLUMNS))), columns=COLUMNS)
        self.set_index([INDEX], drop=True, inplace=True)


class WLDataset(EmptyWLDataset):
    def __init__(self, data, columns):
        super().__init__()
        df = pd.DataFrame(data, columns=columns)
        for column in columns:
            for colname, regex in COL_REGEX.items():
                str_ = column.replace(" ", "").replace("_", "")
                if re.search(regex, str_, re.IGNORECASE):
                    self[colname] = df[column].copy()
                    break
        del df
        self.format_numeric_data()
        self.format_datetime_data()

    def format_numeric_data(self):
        """Format the data to floats type."""
        for colname in COLUMNS:
            if colname == INDEX:
                pass
            elif colname in self.columns:
                self[colname] = pd.to_numeric(self[colname], errors='coerce')
            else:
                print('WARNING: no "%s" data found in the datafile.' % colname)

    def format_datetime_data(self):
        """Format the dates to datetimes and set it as index."""
        if INDEX in self.columns:
            try:
                # We assume first that the dates are stored in the
                # Excel numeric format.
                datetimes = self['Time'].astype('float64', errors='raise')
                datetimes = pd.to_datetime(datetimes.apply(
                    lambda date: xlrd.xldate.xldate_as_datetime(date, 0)))
            except ValueError:
                try:
                    # Try converting the strings to datetime objects.
                    # The format of the datetime strings must be
                    # "%Y-%m-%d %H:%M:%S"
                    datetimes = pd.to_datetime(
                        self['Time'], infer_datetime_format=True)
                except ValueError:
                    print('WARNING: the dates are not formatted correctly.')
            finally:
                self['Time'] = datetimes
                self.set_index(['Time'], drop=True, inplace=True)
        else:
            print('WARNING: no "Time" data found in the datafile.')

        # Check and remove duplicate data.
        if any(self.index.duplicated(keep='first')):
            print("WARNING: Duplicated values were found in the datafile. "
                  "Only the first entries for each date were kept.")
            self.drop_duplicates(keep='first', inplace=True)


def open_water_level_datafile(filename):
    """Open a water level data file and return the data."""
    root, ext = os.path.splitext(filename)
    if ext not in FILE_EXTS:
        raise ValueError("Supported file format are: ", FILE_EXTS)
    else:
        print('Loading waterlvl time-series from "%s"...' %
              osp.basename(filename))

    if ext == '.csv':
        with open(filename, 'r', encoding='utf8') as f:
            data = list(csv.reader(f, delimiter=','))
    elif ext in ['.xls', '.xlsx']:
        with xlrd.open_workbook(filename, on_demand=True) as wb:
            sheet = wb.sheet_by_index(0)
            data = [sheet.row_values(rowx, start_colx=0, end_colx=None) for
                    rowx in range(sheet.nrows)]

    return data


def read_water_level_datafile(filename):
    """
    Load a water level dataset from a csv or an Excel file and format the
    data in a Pandas dataframe with the dates used as index.
    """
    if filename is None or not osp.exists(filename):
        return None
    reader = open_water_level_datafile(filename)

    # Fetch the metadata from the header.
    header = deepcopy(HEADER)
    for i, row in enumerate(reader):
        if not len(row):
            continue
        label = str(row[0]).replace(" ", "").replace("_", "")
        for key in HEADER.keys():
            if re.search(HEADER_REGEX[key], label, re.IGNORECASE):
                if isinstance(header[key], (float, int)):
                    try:
                        header[key] = float(row[1])
                    except ValueError:
                        print('Wrong format for entry "{}".'.format(key))
                else:
                    header[key] = str(row[1])
                break
        else:
            if re.search(COL_REGEX[INDEX], label, re.IGNORECASE):
                break
    else:
        print("ERROR: the water level datafile is not formatted correctly.")
        return None

    # Cast the data into a Pandas dataframe.
    dataf = WLDataset(reader[i+1:], columns=row)

    # Add the metadata to the dataframe.
    for key in header.keys():
        setattr(dataf, key, header[key])
    dataf.filename = filename

    return dataf


# ---- Water Level Manual Measurements
def init_waterlvl_measures(dirname):
    """
    Create an empty waterlvl_manual_measurements.csv file with headers
    if it does not already exist.
    """
    for ext in FILE_EXTS:
        fname = os.path.join(dirname, "waterlvl_manual_measurements" + ext)
        if os.path.exists(fname):
            return
    else:
        fname = os.path.join(dirname, 'waterlvl_manual_measurements.csv')
        fcontent = [['Well_ID', 'Time (days)', 'Obs. (mbgs)']]

        if not os.path.exists(dirname):
            os.makedirs(dirname)
        save_content_to_csv(fname, fcontent)


def load_waterlvl_measures(filename, well):
    """
    Load and read the water level manual measurements from the specified
    resource file for the specified well.
    """
    print('Loading manual water level measures for well %s...' % well, end=" ")
    time_mes, wl_mes = np.array([]), np.array([])
    # Determine the extension of the file.
    root, ext = os.path.splitext(filename)
    exts = [ext] if ext in FILE_EXTS else FILE_EXTS
    for ext in exts:
        filename = root+ext
        if os.path.exists(root+ext):
            break
    else:
        # The file does not exists, so we generate an empty file with
        # a header.
        print("none")
        init_waterlvl_measures(os.path.dirname(root))
        return time_mes, wl_mes

    # Open and read the file.
    if ext == '.csv':
        with open(filename, 'r') as f:
            reader = np.array(list(csv.reader(f, delimiter=',')))
            data = np.array(reader[1:])

            well_name = np.array(data[:, 0]).astype('str')
            time = np.array(data[:, 1]).astype('float')
            wl = np.array(data[:, 2]).astype('float')

    elif ext in ['.xlsx', '.xls']:
        with xlrd.open_workbook(filename) as wb:
            sheet = wb.sheet_by_index(0)

            well_name = sheet.col_values(0, start_rowx=1, end_rowx=None)
            time = sheet.col_values(1, start_rowx=1, end_rowx=None)
            wl = sheet.col_values(2, start_rowx=1, end_rowx=None)

            well_name = np.array(well_name).astype('str')
            time = np.array(time).astype('float')
            wl = np.array(wl).astype('float')

    if len(well_name) > 0:
        rowx = np.where(well_name == well)[0]
        if len(rowx) > 0:
            wl_mes = wl[rowx]
            time_mes = time[rowx]
    print("done")

    return time_mes, wl_mes


def generate_HTML_table(name, lat, lon, alt, mun):

    FIELDS = [['Well Name', name],
              ['Latitude', '%0.3f°' % lat],
              ['Longitude', '%0.3f°' % lon],
              ['Altitude', '%0.1f m' % alt],
              ['Municipality', mun]]

    table = '<table border="0" cellpadding="2" cellspacing="0" align="left">'
    for row in FIELDS:
        table += '''
                 <tr>
                   <td width=10></td>
                   <td align="left">%s</td>
                   <td align="left" width=20>:</td>
                   <td align="left">%s</td>
                   </tr>
                 ''' % (row[0], row[1])
    table += '</table>'

    return table


class WLDataFrameBase(Mapping):
    """
    A water level data frame base class.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dset = None
        self._undo_stack = []
        self._dataf = EmptyWLDataset()

    def __load_dataset__(self):
        """Loads the dataset and save it in a store."""
        raise NotImplementedError

    def __len__(self, key):
        return len(self._datetimes)

    def __setitem__(self, key, value):
        return NotImplementedError

    def __iter__(self):
        return NotImplementedError

    # ---- Attributes
    @property
    def data(self):
        return self._dataf

    @property
    def xldates(self):
        """
        Return a numpy array containing the Excel numerical dates
        corresponding to the dates of the dataset.
        """
        if 'XLDATES' not in self._dataf.columns:
            print('Converting datetimes to xldates...', end=' ')
            timedeltas = (
                self._dataf.index - xlrd.xldate.xldate_as_datetime(4000, 0))
            self._dataf['XLDATES'] = (
                timedeltas.total_seconds()/(3600 * 24) + 4000)
            print('done')
        return self._dataf['XLDATES'].values

    @property
    def dates(self):
        return self.data.index.values

    @property
    def strftime(self):
        return self.data.index.strftime("%Y-%m-%dT%H:%M:%S").values.tolist()

    @property
    def waterlevels(self):
        return self.data['WL'].values

    # ---- Versionning
    @property
    def has_uncommited_changes(self):
        """"
        Return whether there is uncommited changes to the water level data.
        """
        return bool(len(self._undo_stack))

    def commit(self):
        """Commit the changes made to the water level data to the project."""
        raise NotImplementedError

    def undo(self):
        """Undo the last changes made to the water level data."""
        if self.has_uncommited_changes:
            changes = self._undo_stack.pop(-1)
            self._dataf['WL'][changes.index] = changes

    def clear_all_changes(self):
        """
        Clear all changes that were made to the water level data since the
        last commit.
        """
        while self.has_uncommited_changes:
            self.undo()

    def delete_waterlevels_at(self, indexes):
        """Delete the water level data at the specified indexes."""
        if len(indexes):
            self._add_to_undo_stack(indexes)
            self._dataf['WL'].iloc[indexes] = np.nan

    def _add_to_undo_stack(self, indexes):
        """
        Store the old water level values at the specified indexes in a stack
        before changing or deleting them. This allow to undo or cancel any
        changes made to the water level data before commiting them.
        """
        if len(indexes):
            self._undo_stack.append(self._dataf['WL'].iloc[indexes].copy())


class WLDataFrame(WLDataFrameBase):
    """
    A water level dataset container that loads its data from a csv
    or an Excel file.
    """

    def __init__(self, filename, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__load_dataset__(filename)

    def __getitem__(self, key):
        """Returns the value saved in the store at key."""
        if key == INDEX:
            return self.strftime
        elif key in COLUMNS:
            return self.data[key].values
        elif key in list(HEADER.keys()):
            return getattr(self._dataf, key, HEADER[key])
        elif key == 'filename':
            return self._dataf.filename

        return self.dset.__getitem__(key)

    def __load_dataset__(self, filename):
        """Loads the dataset from a file and saves it in the store."""
        self._dataf = read_water_level_datafile(filename)


if __name__ == "__main__":
    from gwhat import __rootdir__
    df = WLDataFrame(
        osp.join(__rootdir__, 'tests', "water_level_datafile.csv"))
    df2 = WLDataFrame(
        osp.join(__rootdir__, 'tests', "water_level_datafile.xls"))
    df3 = WLDataFrame(
        osp.join(__rootdir__, 'tests', "water_level_datafile.xlsx"))
