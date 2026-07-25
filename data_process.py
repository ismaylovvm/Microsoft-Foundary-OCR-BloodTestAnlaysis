import re
 
 
def determine_status(value_str, reference_range_str):
    
   
    if "[H]" in value_str:
        return "high"
    if "[L]" in value_str:
        return "low"
 
    value_match = re.search(r"[\d.]+", value_str)
    if not value_match:
        return "unknown"
    value_num = float(value_match.group())
 
    range_match = re.search(r"([\d.]+)\s*-\s*([\d.]+)", reference_range_str)
    if not range_match:
        return "unknown"
    min_val = float(range_match.group(1))
    max_val = float(range_match.group(2))
 
    if value_num < min_val:
        return "low"
    elif value_num > max_val:
        return "high"
    else:
        return "normal"
 
 
def parse_table(result):
    """
    Returns:
        [
            {"test_name": "Haemoglobin", "value": "9.10", "unit": "gm/dl",
             "reference_range": "13.0-17.0 gm/dl", "status": "low"},
            ...
        ]
    """
    parsed_results = []
 
    for table in result.tables:
        rows = {}
        for cell in table.cells:
            rows.setdefault(cell.row_index, {})[cell.column_index] = cell.content
 
        for row_idx, cols in rows.items():
 
           
            raw_test_name = cols.get(0, "").strip()
            raw_value = cols.get(1, "").strip()
            unit = cols.get(2, "").strip()
            reference_range = cols.get(3, "").strip()
 
            if not raw_test_name or not raw_value:
                continue
 
            test_name = raw_test_name.rstrip(" :")
 
            
            status = determine_status(raw_value, reference_range)
 
            clean_value = re.sub(r"\[[HL]\]", "", raw_value).strip()
 
            parsed_results.append({
                "test_name": test_name,
                "value": clean_value,
                "unit": unit,
                "reference_range": reference_range,
                "status": status,
            })
 
    return parsed_results

 
 
def to_documents(results):
 
    documents = []
    for row in results:
        sentence = (
            f"{row['test_name']} test result was measured as {row['value']} {row['unit']}. "
            f"The normal reference range is {row['reference_range']}. "
            f"This value was evaluated as {row['status']}."
        )
        documents.append(sentence)
    return documents