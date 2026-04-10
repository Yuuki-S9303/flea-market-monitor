/**
 * スプレッドシートの初期セットアップ
 * - シートの作成・リネーム
 * - ヘッダー行の設定
 *
 * 使い方: GASエディタで実行ボタンを押すだけ
 */

function setupSheets() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  // ── シート定義 ──────────────────────────────────────
  const sheets = [
    {
      name: "キーワードリスト",
      headers: ["キーワード", "種類"],
      // 種類: 空欄=キーワード指定型（生データ（キーワード指定）に書き込み）
      //       "探索"=探索型（生データ（探索）に書き込み）
      samples: [
        ["スリコ", ""],
        ["ダイソー", ""],
        ["業務スーパー", "探索"],
        ["ポケカ", "探索"],
      ],
    },
    {
      name: "生データ（キーワード指定）",
      headers: [
        "取得日時", "プラットフォーム", "検索キーワード", "商品ID",
        "商品名", "価格", "売れた日時", "商品状態", "カテゴリ",
        "サムネイルURL", "商品URL",
      ],
    },
    {
      name: "生データ（探索）",
      headers: [
        "取得日時", "プラットフォーム", "検索キーワード", "商品ID",
        "商品名", "価格", "売れた日時", "商品状態", "カテゴリ",
        "サムネイルURL", "商品URL",
      ],
    },
    {
      name: "集計",
      headers: ["商品名", "プラットフォーム", "売れ数", "平均価格", "最高価格", "最低価格", "直近売れた日時"],
    },
    {
      name: "キーワード候補",
      headers: ["キーワード候補", "発掘元", "メモ", "追加済み"],
    },
    {
      name: "仕入れ管理",
      headers: [
        "商品名", "プラットフォーム", "商品URL", "サムネイルURL",
        "参入日", "仕入れステータス", "メモ", "直近売れ数", "直近平均価格",
      ],
    },
  ];

  // ── 既存シートを「シート1」以外は削除しない（安全のため追加のみ） ──
  // 「シート1」を「キーワードリスト」にリネーム
  const defaultSheet = ss.getSheetByName("シート1");
  if (defaultSheet) {
    defaultSheet.setName("キーワードリスト");
  }

  // ── 各シートを作成・ヘッダー設定 ──────────────────────
  sheets.forEach(({ name, headers, samples }) => {
    let sheet = ss.getSheetByName(name);
    if (!sheet) {
      sheet = ss.insertSheet(name);
    }

    // ヘッダー行が空の場合のみ設定
    if (!sheet.getRange("A1").getValue()) {
      sheet.getRange(1, 1, 1, headers.length).setValues([headers]);

      // ヘッダー行のスタイル
      const headerRange = sheet.getRange(1, 1, 1, headers.length);
      headerRange.setBackground("#4a86e8");
      headerRange.setFontColor("#ffffff");
      headerRange.setFontWeight("bold");
      sheet.setFrozenRows(1);

      // 列幅を自動調整
      sheet.autoResizeColumns(1, headers.length);
    }

    // キーワードリストにサンプルデータを追加
    if (name === "キーワードリスト" && samples) {
      const startRow = sheet.getLastRow() + 1;
      if (startRow === 2) {  // ヘッダーのみの場合
        samples.forEach((row, i) => {
          if (Array.isArray(row)) {
            sheet.getRange(2 + i, 1, 1, row.length).setValues([row]);
          } else {
            sheet.getRange(2 + i, 1).setValue(row);
          }
        });
      }
    }

    // キーワードリストの「種類」列にドロップダウン設定
    if (name === "キーワードリスト") {
      const kindRule = SpreadsheetApp.newDataValidation()
        .requireValueInList(["", "探索"], true)
        .build();
      sheet.getRange("B2:B1000").setDataValidation(kindRule);
    }

    // 仕入れ管理シートにドロップダウン設定
    if (name === "仕入れ管理") {
      const rule = SpreadsheetApp.newDataValidation()
        .requireValueInList(["参入中", "様子見", "撤退"], true)
        .build();
      sheet.getRange("F2:F1000").setDataValidation(rule);
    }
  });

  SpreadsheetApp.getUi().alert("セットアップ完了！シートとヘッダーを設定しました。");
}
