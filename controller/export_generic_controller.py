import logging
import pandas as pd
from io import BytesIO
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

def _flatten_values(value, prefix=""):
    rows = []

    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            rows.extend(_flatten_values(child, child_prefix))
        return rows

    if isinstance(value, list):
        for index, child in enumerate(value, start=1):
            child_prefix = f"{prefix}[{index}]" if prefix else f"[{index}]"
            rows.extend(_flatten_values(child, child_prefix))
        return rows

    rows.append({"Field": prefix, "Value": value})
    return rows


def _make_dataframe(sheet_data):
    if isinstance(sheet_data, list) and sheet_data and all(
        isinstance(item, dict) for item in sheet_data
    ):
        return pd.json_normalize(sheet_data, sep=".")

    if isinstance(sheet_data, dict):
        rows = _flatten_values(sheet_data)
        return pd.DataFrame(rows or [{"Field": "Message", "Value": "No data available"}])

    if isinstance(sheet_data, list):
        return pd.DataFrame({"Value": sheet_data})

    return pd.DataFrame([{"Value": sheet_data}])


def _generic_json_to_excel(data_dict: dict) -> BytesIO:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        if not data_dict:
            pd.DataFrame([{"Message": "No data available"}]).to_excel(writer, sheet_name="No Data", index=False)
        else:
            used_sheet_names = set()
            for sheet_name, sheet_data in data_dict.items():
                base_name = str(sheet_name)[:31].replace(":", "_").replace("/", "_").replace("\\", "_")
                safe_sheet_name = base_name or "Report"
                suffix = 2
                while safe_sheet_name in used_sheet_names:
                    suffix_text = f"_{suffix}"
                    safe_sheet_name = f"{base_name[:31 - len(suffix_text)]}{suffix_text}"
                    suffix += 1
                used_sheet_names.add(safe_sheet_name)

                df = _make_dataframe(sheet_data)
                df.columns = [str(column) for column in df.columns]
                df.to_excel(writer, sheet_name=safe_sheet_name, index=False)

                worksheet = writer.book[safe_sheet_name]
                worksheet.freeze_panes = "A2"
                worksheet.auto_filter.ref = worksheet.dimensions
                for column_cells in worksheet.columns:
                    column_letter = column_cells[0].column_letter
                    max_length = max(len(str(cell.value or "")) for cell in column_cells)
                    worksheet.column_dimensions[column_letter].width = min(max(max_length + 2, 14), 45)
                    for cell in column_cells:
                        cell.alignment = cell.alignment.copy(wrap_text=True, vertical="top")

                for cell in worksheet[1]:
                    cell.font = cell.font.copy(bold=True, color="FFFFFF")
                    cell.fill = cell.fill.copy(fill_type="solid", fgColor="002060")

    output.seek(0)
    return output

def _flatten_gst_report(report_data):
    """Flattens the GST report format which is often a list of dicts."""
    data_dict = {}
    if isinstance(report_data, list):
        for i, item in enumerate(report_data):
            if isinstance(item, dict):
                for k, v in item.items():
                    data_dict[f"{k}_{i}"] = v
    elif isinstance(report_data, dict):
        data_dict = report_data
    return data_dict

async def export_gst_report_generic(db, user_id: str, reference_id: str = None) -> StreamingResponse:
    gst_report_coll = db["gst_analyzed_report"]
    query = {"user_id": user_id}
    if reference_id:
        query["reference_id"] = reference_id
    
    doc = await gst_report_coll.find_one(query)
    
    if not doc or not doc.get("report"):
        raise HTTPException(status_code=404, detail={"message": "GST data not found"})
        
    report = doc["report"]
    data_dict = _flatten_gst_report(report)
        
    excel_file = _generic_json_to_excel(data_dict)
    filename = f"GST_Report_{reference_id or user_id}.xlsx"
    
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

async def export_itr_report_generic(db, user_id: str) -> StreamingResponse:
    itr_repo = db["itr_analyzed_report"]
    doc = await itr_repo.find_one({"user_id": user_id})
    
    if not doc or not doc.get("report"):
        raise HTTPException(status_code=404, detail={"message": "ITR data not found"})
        
    data_dict = doc.get("report")
    if not isinstance(data_dict, dict):
         data_dict = {"ITR_Data": data_dict}
         
    excel_file = _generic_json_to_excel(data_dict)
    filename = f"ITR_Report_{user_id}.xlsx"
    
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

async def export_cibil_report_generic(
    db,
    reference_id: str,
    user_id: str,
) -> StreamingResponse:
    cibil_repo = db["cibil_report"]
    doc = await cibil_repo.find_one(
        {
            "reference_id": reference_id,
            "user_id": user_id,
        }
    )
    
    if not doc or not doc.get("cibil_report"):
        raise HTTPException(status_code=404, detail={"message": "CIBIL data not found"})
        
    data_dict = doc.get("cibil_report")
    if not isinstance(data_dict, dict):
         data_dict = {"CIBIL_Data": data_dict}
         
    excel_file = _generic_json_to_excel(data_dict)
    filename = f"CIBIL_Report_{reference_id}.xlsx"
    
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
