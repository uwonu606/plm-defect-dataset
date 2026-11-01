import sys,openpyxl
wb=openpyxl.load_workbook(sys.argv[1],read_only=True)
for ws in wb.worksheets:
    rows=list(ws.iter_rows(values_only=True))
    print(ws.title,len(rows))
    for r in rows[:4]: print([str(x)[:40] for x in r if x is not None][:12])
