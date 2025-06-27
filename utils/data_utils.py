import os
import pandas as pd
from typing import List, Optional
from utils.logger import logger


def check_file_exists(file_path: str) -> bool:
    """ファイルの存在確認（ログ付き）"""
    if os.path.exists(file_path):
        logger.info(f"File exists: {file_path}")
        return True
    else:
        logger.error(f"File not found: {file_path}")
        return False


def read_csv_with_log(file_path: str, encoding: str = 'utf-8') -> Optional[pd.DataFrame]:
    """CSVファイルを読み込み、成功/失敗をログ出力"""
    try:
        df = pd.read_csv(file_path, encoding=encoding)
        logger.info(f"File readable: {len(df)} rows loaded from {file_path}")
        return df
    except Exception as e:
        logger.error(f"File not readable: {file_path} ({e})")
        return None


def check_required_columns(df: pd.DataFrame, required_columns: List[str]) -> List[str]:
    """必須カラムがDataFrameに存在するか検証し、足りないカラム名リストを返す"""
    missing = [col for col in required_columns if col not in df.columns]
    if not missing:
        logger.info("All required columns present")
    else:
        logger.error(f"Missing required columns: {missing}")
    return missing


def find_duplicates(df: pd.DataFrame, subset: List[str]) -> pd.DataFrame:
    """指定カラムで重複している行を返す"""
    duplicates = df[df.duplicated(subset=subset, keep=False)]
    if not duplicates.empty:
        logger.warning(f"Duplicate rows found for subset {subset}: {len(duplicates)} rows")
    return duplicates


def detect_outliers(df: pd.DataFrame, column: str, stddev: float = 3.0) -> pd.DataFrame:
    """指定カラムで平均±stddev*標準偏差から外れる外れ値行を返す"""
    mean = df[column].mean()
    std = df[column].std()
    outliers = df[(df[column] < mean - stddev * std) | (df[column] > mean + stddev * std)]
    if not outliers.empty:
        logger.warning(f"Outliers detected in {column}: {len(outliers)} rows")
    return outliers 