import pandas as pd
import numpy as np
from core.logger import logger


def reduce_mem_usage(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pandas DataFrame belleğini optimize eder (Downcasting).
    float64 -> float32
    int64 -> int32, int16, int8

    Bu işlem, RAM kullanımını %50 ila %70 arasında düşürür.

    Args:
        df: Optimize edilecek DataFrame

    Returns:
        pd.DataFrame: Optimize edilmiş DataFrame
    """
    if df is None or df.empty:
        return df

    try:
        start_mem = df.memory_usage().sum() / 1024**2
        logger.debug(f"Memory usage of dataframe is {start_mem:.2f} MB")

        for col in df.columns:
            col_type = df[col].dtype

            if (
                col_type is not object
                and not isinstance(col_type, pd.CategoricalDtype)
                and not pd.api.types.is_datetime64_any_dtype(col_type)
            ):
                c_min = df[col].min()
                c_max = df[col].max()

                # Check for NaNs before casting to integer, as integer arrays in older pandas cannot hold NaNs
                # (unless using nullable integer types like Int64, which can be slower or less compatible with TA-Lib).
                # To be safe with TA-Lib and standard pandas operations, we only cast to int if there are no NaNs.
                has_nan = df[col].isna().any()

                if str(col_type)[:3] == "int" and not has_nan:
                    if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                        df[col] = df[col].astype(np.int8)
                    elif (
                        c_min > np.iinfo(np.int16).min
                        and c_max < np.iinfo(np.int16).max
                    ):
                        df[col] = df[col].astype(np.int16)
                    elif (
                        c_min > np.iinfo(np.int32).min
                        and c_max < np.iinfo(np.int32).max
                    ):
                        df[col] = df[col].astype(np.int32)
                    elif (
                        c_min > np.iinfo(np.int64).min
                        and c_max < np.iinfo(np.int64).max
                    ):
                        df[col] = df[col].astype(np.int64)
                else:
                    # It's a float or int with NaNs. Cast to float32 to save memory,
                    # as float32 provides ~7 decimal digits of precision which is enough for crypto prices/indicators.
                    if (
                        c_min > np.finfo(np.float32).min
                        and c_max < np.finfo(np.float32).max
                    ):
                        df[col] = df[col].astype(np.float32)
                    else:
                        df[col] = df[col].astype(np.float64)

        end_mem = df.memory_usage().sum() / 1024**2
        reduction = 100 * (start_mem - end_mem) / start_mem
        logger.info(
            f"Memory usage after optimization is: {end_mem:.2f} MB. Decreased by {reduction:.1f}%"
        )

        return df
    except Exception as e:
        logger.error(f"Error during memory reduction: {e}")
        return df
