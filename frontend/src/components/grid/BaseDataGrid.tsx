"use client";

import { Card } from "@mui/material";
import {
  DataGrid,
  GridColDef,
  GridDensity,
  GridRowParams,
  GridRowsProp,
  GridToolbar,
} from "@mui/x-data-grid";

export function BaseDataGrid({
  rows,
  columns,
  height = 460,
  density,
  onRowClick,
  rowSelectionModel,
}: {
  rows: GridRowsProp;
  columns: GridColDef[];
  height?: number;
  density?: GridDensity;
  onRowClick?: (params: GridRowParams) => void;
  rowSelectionModel?: (string | number)[];
}) {
  return (
    <Card
      elevation={0}
      sx={{
        height,
        border: "1px solid #dde5f0",
        "& .MuiDataGrid-root": { border: 0 },
        "& .MuiDataGrid-cell": {
          display: "flex",
          alignItems: "center",
          overflow: "hidden",
        },
        "& .MuiDataGrid-row.Mui-selected": {
          backgroundColor: "#eff6ff",
          borderLeft: "3px solid #3b82f6",
          "&:hover": { backgroundColor: "#dbeafe" },
        },
        "& .MuiDataGrid-row.Mui-selected .MuiDataGrid-cell:first-of-type": {
          paddingLeft: "9px",
        },
      }}
    >
      <DataGrid
        rows={rows}
        columns={columns}
        disableRowSelectionOnClick={!onRowClick}
        slots={{ toolbar: GridToolbar }}
        onRowClick={onRowClick}
        density={density}
        pageSizeOptions={[10, 25, 50]}
        rowSelectionModel={rowSelectionModel}
        initialState={{
          pagination: {
            paginationModel: { pageSize: 10, page: 0 },
          },
        }}
      />
    </Card>
  );
}
