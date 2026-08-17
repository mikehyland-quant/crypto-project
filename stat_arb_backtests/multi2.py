
import pandas as pd
import xlwings as xw
from pathlib import Path


# ============================================================
# USER INPUTS
# ============================================================

analysis_year = 2026

input_folder = f"combined_analysis_{analysis_year}"

output_file = f"all_combined_{analysis_year}.xlsx"

summary_sheet = "summary"


# ============================================================
# DIRECTORIES
# ============================================================

# This script lives in the stat_arb directory.
base_dir = Path(__file__).resolve().parent

input_dir = base_dir / input_folder

output_path = base_dir / output_file


# ============================================================
# GET ALL EXCEL FILES
# ============================================================

file_list = sorted(
    input_dir.glob("*.xlsx")
)

# Exclude the output file if it already exists in the folder.
file_list = [
    file
    for file in file_list
    if not file.name.startswith("all_combined")
]


# ============================================================
# STORAGE FOR SUMMARY RESULTS
# ============================================================

all_summary_rows = []


# ============================================================
# START EXCEL
# ============================================================

app = xw.App(
    visible=False,
    add_book=False,
)


try:

    # ========================================================
    # LOOP THROUGH EACH FILE
    # ========================================================

    for file_path in file_list:

        print(f"Reading: {file_path.name}")

        wb = app.books.open(
            file_path
        )

        try:

            ws = wb.sheets[
                summary_sheet
            ]


            # =================================================
            # READ SUMMARY DATA
            # =================================================

            summary_data = (
                ws.range("A1")
                .expand()
                .value
            )


            # =================================================
            # CONVERT TO DATAFRAME
            # =================================================

            summary_df = pd.DataFrame(
                summary_data[1:],
                columns=summary_data[0],
            )


            # =================================================
            # CONVERT SUMMARY INTO ONE ROW
            # =================================================

            summary_dict = dict(
                zip(
                    summary_df["stat"],
                    summary_df["value"],
                )
            )


            # =================================================
            # ADD FILE NAME
            # =================================================

            summary_dict[
                "file_name"
            ] = file_path.name


            # =================================================
            # SAVE ROW
            # =================================================

            all_summary_rows.append(
                summary_dict
            )


        finally:

            wb.close()


finally:

    app.quit()


# ============================================================
# CREATE MASTER DATAFRAME
# ============================================================

all_combined_df = pd.DataFrame(
    all_summary_rows
)


# ============================================================
# MOVE IMPORTANT COLUMNS TO FRONT
# ============================================================

front_cols = [
    "file_name",
    "first_parameter",
    "second_parameter",
]

front_cols = [
    col
    for col in front_cols
    if col in all_combined_df.columns
]

other_cols = [
    col
    for col in all_combined_df.columns
    if col not in front_cols
]

all_combined_df = all_combined_df[
    front_cols + other_cols
]


# ============================================================
# SORT BY PARAMETERS
# ============================================================

sort_cols = [
    col
    for col in [
        "first_parameter",
        "second_parameter",
    ]
    if col in all_combined_df.columns
]

if sort_cols:

    all_combined_df.sort_values(
        by=sort_cols,
        inplace=True,
    )

    all_combined_df.reset_index(
        drop=True,
        inplace=True,
    )


# ============================================================
# PRINT RESULTS
# ============================================================

print()
print("ALL COMBINED RESULTS")
print("--------------------")

print(
    all_combined_df.to_string(
        index=False
    )
)

print()


# ============================================================
# SAVE MASTER DATAFRAME TO EXCEL
# ============================================================

app = xw.App(
    visible=False,
    add_book=True,
)

try:

    wb = app.books[0]

    ws = wb.sheets[0]

    ws.name = "all_combined"


    # ========================================================
    # WRITE DATAFRAME
    # ========================================================

    ws.range("A1").options(
        index=False,
        header=True,
    ).value = all_combined_df


    # ========================================================
    # FORMAT
    # ========================================================

    ws.range(
        "1:1"
    ).api.Font.Bold = True

    ws.autofit()


    # ========================================================
    # SAVE
    # ========================================================

    wb.save(
        output_path
    )

    wb.close()


finally:

    app.quit()


# ============================================================
# FINISHED
# ============================================================

print(
    f"Saved to: {output_path}"
)
