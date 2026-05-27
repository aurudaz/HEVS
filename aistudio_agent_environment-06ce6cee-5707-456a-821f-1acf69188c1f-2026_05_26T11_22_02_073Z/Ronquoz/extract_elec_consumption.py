import zipfile
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np

def extract_excel_to_csv():
    xlsx_path = '/Ronquoz/Laboratoire Ronquoz - 2/elec_consumption.xlsx'
    print(f"Extracting {xlsx_path} to CSV using pure Python zipfile and xml...")
    
    with zipfile.ZipFile(xlsx_path) as z:
        # 1. Parse shared strings
        shared_strings = []
        try:
            sst_tree = ET.parse(z.open('xl/sharedStrings.xml'))
            sst_root = sst_tree.getroot()
            ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            for si in sst_root.findall('.//ns:si', ns):
                # Handle text nodes
                t_nodes = si.findall('.//ns:t', ns)
                if t_nodes:
                    shared_strings.append("".join([t.text or "" for t in t_nodes]))
                else:
                    shared_strings.append("")
        except KeyError:
            print("No shared strings file found.")
        
        print(f"Found {len(shared_strings)} shared strings.")
        
        # 2. Parse sheet2.xml (which corresponds to 'resume' worksheet, linked by rId2)
        sheet_tree = ET.parse(z.open('xl/worksheets/sheet2.xml'))
        sheet_root = sheet_tree.getroot()
        
        ns_sheet = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        
        # We will extract rows
        data_rows = []
        max_col_idx = 0
        
        for row in sheet_root.findall('.//ns:row', ns_sheet):
            row_idx = int(row.attrib['r'])
            row_data = {}
            for cell in row.findall('.//ns:c', ns_sheet):
                r_attr = cell.attrib['r'] # e.g. "A1", "B1"
                t_attr = cell.get('t') # cell type: 's' for shared string, etc.
                
                # Get column letter and index
                col_letter = ''.join([c for c in r_attr if c.isalpha()])
                col_num = 0
                for char in col_letter:
                    col_num = col_num * 26 + (ord(char.upper()) - 64)
                col_idx = col_num - 1 # 0-based index
                max_col_idx = max(max_col_idx, col_idx)
                
                val_node = cell.find('.//ns:v', ns_sheet)
                val = ""
                if val_node is not None:
                    val = val_node.text or ""
                    if t_attr == 's': # shared string
                        val = shared_strings[int(val)]
                    elif t_attr == 'b': # boolean
                        val = True if val == '1' else False
                    else: # numeric or string
                        try:
                            val = float(val) if '.' in val or 'e' in val.lower() else int(val)
                        except ValueError:
                            pass
                row_data[col_idx] = val
            data_rows.append((row_idx, row_data))
            
        print(f"Parsed {len(data_rows)} rows and up to {max_col_idx + 1} columns.")
        
        # Sort rows by row index
        data_rows.sort(key=lambda x: x[0])
        
        # Create a matrix of data
        num_rows = len(data_rows)
        num_cols = max_col_idx + 1
        
        matrix = [[None] * num_cols for _ in range(num_rows)]
        # We want to map row_idx to its correct position (row_idx - 1)
        for row_idx, row_data in data_rows:
            r_i = row_idx - 1
            if r_i >= num_rows:
                # pad rows
                matrix.extend([[None] * num_cols for _ in range(r_i - len(matrix) + 1)])
            for col_idx, val in row_data.items():
                if col_idx >= len(matrix[r_i]):
                    # pad columns
                    for r in range(len(matrix)):
                        matrix[r].extend([None] * (col_idx - len(matrix[r]) + 1))
                matrix[r_i][col_idx] = val
                
        # Turn into DataFrame
        df = pd.DataFrame(matrix)
        # First row is typically headers
        headers = df.iloc[0].tolist()
        df = df.iloc[1:]
        df.columns = headers
        
        # Clean columns: rename first column if it's None or something
        if df.columns[0] is None or pd.isna(df.columns[0]):
            df.rename(columns={df.columns[0]: 'ID-BAT'}, inplace=True)
            
        print("Columns head:", list(df.columns[:10]))
        print("Data shape:", df.shape)
        
        # Save to CSV
        df.to_csv('/Ronquoz/results/lab2/elec_consumption.csv', index=False)
        print("Saved to /Ronquoz/results/lab2/elec_consumption.csv")

if __name__ == '__main__':
    extract_excel_to_csv()
