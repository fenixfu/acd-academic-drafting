#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/output"
BACKUP_DIR="$SCRIPT_DIR/former_results"
SIMILARITY_THRESHOLD=0.8

DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "=== DRY RUN 模式（不实际执行）==="
    echo
fi

if [[ ! -d "$OUTPUT_DIR" ]]; then
    echo "❌ 错误: output 目录不存在" >&2
    exit 1
fi

OUTPUT_FILES=()
while IFS= read -r -d '' file; do
    OUTPUT_FILES+=("$file")
done < <(find "$OUTPUT_DIR" -type f -print0 2>/dev/null | sort -z)

OUTPUT_COUNT=${#OUTPUT_FILES[@]}

if [[ $OUTPUT_COUNT -eq 0 ]]; then
    echo "⚠️  output 目录为空，无需备份"
    exit 0
fi

echo "=== 备份分析 ==="
echo "output 文件数: $OUTPUT_COUNT"

if [[ ! -d "$BACKUP_DIR" ]]; then
    if $DRY_RUN; then
        echo "[DRY RUN] 将创建: $BACKUP_DIR"
    else
        mkdir -p "$BACKUP_DIR"
    fi
    LATEST_BACKUP=""
else
    LATEST_BACKUP=$(find "$BACKUP_DIR" -maxdepth 1 -type d -name "20[0-9][0-9][0-9][0-9][0-9][0-9]_[0-9][0-9][0-9]" | sort -r | head -1)
fi

MODE="new"
MATCH_COUNT=0

if [[ -n "$LATEST_BACKUP" ]]; then
    LATEST_NAME=$(basename "$LATEST_BACKUP")
    
    BACKUP_FILES=()
    while IFS= read -r -d '' file; do
        BACKUP_FILES+=("$file")
    done < <(find "$LATEST_BACKUP" -type f -print0 2>/dev/null | sort -z)
    
    BACKUP_COUNT=${#BACKUP_FILES[@]}
    
    MATCH_COUNT=0
    for out_file in "${OUTPUT_FILES[@]}"; do
        REL_PATH="${out_file#$OUTPUT_DIR/}"
        BACKUP_FILE="$LATEST_BACKUP/$REL_PATH"
        
        if [[ -f "$BACKUP_FILE" ]]; then
            OUT_HASH=$(md5sum "$out_file" 2>/dev/null | cut -d' ' -f1)
            BACKUP_HASH=$(md5sum "$BACKUP_FILE" 2>/dev/null | cut -d' ' -f1)
            
            if [[ "$OUT_HASH" == "$BACKUP_HASH" ]]; then
                MATCH_COUNT=$((MATCH_COUNT + 1))
            fi
        fi
    done
    
    if [[ $OUTPUT_COUNT -gt 0 ]]; then
        SIMILARITY=$(echo "scale=2; $MATCH_COUNT / $OUTPUT_COUNT" | bc)
    else
        SIMILARITY=0
    fi
    
    SIMILARITY_PERCENT=$(echo "scale=0; $SIMILARITY * 100" | bc)
    
    echo "最新备份: $LATEST_NAME ($BACKUP_COUNT 个文件)"
    echo "hash 匹配: $MATCH_COUNT/$OUTPUT_COUNT (${SIMILARITY_PERCENT}%)"
    
    IS_SIMILAR=$(echo "$SIMILARITY >= $SIMILARITY_THRESHOLD" | bc -l)
    if [[ "$IS_SIMILAR" == "1" ]]; then
        echo "→ 追加模式"
        MODE="append"
    else
        echo "→ 新建备份"
    fi
else
    echo "无历史备份 → 新建备份"
fi

echo
echo "=== 执行备份 ==="

if [[ "$MODE" == "append" ]]; then
    NEW_FILES=()
    for out_file in "${OUTPUT_FILES[@]}"; do
        REL_PATH="${out_file#$OUTPUT_DIR/}"
        BACKUP_FILE="$LATEST_BACKUP/$REL_PATH"
        
        if [[ ! -f "$BACKUP_FILE" ]]; then
            NEW_FILES+=("$out_file|$REL_PATH")
        fi
    done
    
    if [[ ${#NEW_FILES[@]} -eq 0 ]]; then
        echo "无新增文件，跳过复制"
    else
        echo "新增文件:"
        for entry in "${NEW_FILES[@]}"; do
            REL_PATH="${entry#*|}"
            echo "  + $REL_PATH"
        done
        echo
        
        if $DRY_RUN; then
            echo "[DRY RUN] 将复制 ${#NEW_FILES[@]} 个文件到: $LATEST_BACKUP/"
        else
            for entry in "${NEW_FILES[@]}"; do
                SRC_FILE="${entry%|*}"
                REL_PATH="${entry#*|}"
                DEST_FILE="$LATEST_BACKUP/$REL_PATH"
                
                DEST_DIR=$(dirname "$DEST_FILE")
                mkdir -p "$DEST_DIR"
                cp "$SRC_FILE" "$DEST_FILE"
            done
            echo "已复制到: $LATEST_BACKUP/"
        fi
    fi
    TARGET_DIR="$LATEST_BACKUP"
else
    TODAY=$(date +%Y%m%d)
    
    TODAY_COUNT=$(find "$BACKUP_DIR" -maxdepth 1 -type d -name "${TODAY}_[0-9][0-9][0-9]" 2>/dev/null | wc -l)
    SEQ=$((TODAY_COUNT + 1))
    SEQ_STR=$(printf "%03d" $SEQ)
    
    NEW_BACKUP_NAME="${TODAY}_${SEQ_STR}"
    TARGET_DIR="$BACKUP_DIR/$NEW_BACKUP_NAME"
    
    if $DRY_RUN; then
        echo "[DRY RUN] 将创建: $NEW_BACKUP_NAME/"
        echo "[DRY RUN] 将复制 $OUTPUT_COUNT 个文件"
    else
        mkdir -p "$TARGET_DIR"
        
        for out_file in "${OUTPUT_FILES[@]}"; do
            REL_PATH="${out_file#$OUTPUT_DIR/}"
            DEST_FILE="$TARGET_DIR/$REL_PATH"
            DEST_DIR=$(dirname "$DEST_FILE")
            mkdir -p "$DEST_DIR"
            cp "$out_file" "$DEST_FILE"
        done
        
        echo "新建备份: $NEW_BACKUP_NAME/ ($OUTPUT_COUNT 个文件)"
    fi
fi

echo
if $DRY_RUN; then
    echo "[DRY RUN] 将询问是否清空 output/"
else
    read -p "清空 output/ 目录? [y/N]: " CONFIRM
    if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
        rm -rf "${OUTPUT_DIR:?}"/*
        echo "✓ 已清空 output/"
    else
        echo "✓ 已跳过清空"
    fi
fi

echo
echo "备份完成。"
