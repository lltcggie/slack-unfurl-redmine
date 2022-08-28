# slack-unfurl-redmine

## 概要
Slackでアクセス制限があるRedmineのタイトルを表示するBot。  
Issuesの場合は説明の一部も表示する。  
ソケットモードで動作するのでWebサーバーが不要。

## インストール方法

### 1. docker-compose.ymlの用意
1. `docker-compose.yml.template` をコピーして `docker-compose.yml` を用意する
2. `ADMIN_USER_ID_LIST` にAPIキーを管理するユーザーのIDを入力する  
複数人いる場合は `U02UB5FEUH2;U03TW5V9CMV` のように;区切りで入力すること

設定値のうち `SLACK_*` は `2. Slack Appの作成` で生成される値なので `docker-compose.yml` にコピーすること。

### 2. Slack Appの作成

1. https://api.slack.com/apps の Create New App からアプリ作成
2. 左メニュー Socket Mode を開き、Enable Socket ModeをOnに変更、App Tokenをクリップボードにコピー (`SLACK_APP_TOKEN`)
3. 左メニュー OAuth & Permissions を開き、 Scopes で link:write を追加
4. 左メニュー Event Subscriptions を開き、 Enable Events を On に変更
    - App unfurl domains を展開し、 Add Domain で使用するドメイン 例 `www.redmine.org` を入力して Save Changes
5. 左メニュー Slash Commands を開き、以下のコマンドを追加する
    - /redmine_register_api_key
    - /redmine_list_registered_api_key
5. 左メニュー Install App を開き、 Install App to Workspace -> Allow
6. OAuth Access Token が表示されるのでクリップボードにコピー (`SLACK_BOT_TOKEN`)

### 3. Docker Composeで起動する

## 初期セットアップ方法
使用するチャンネルに対して以下のセットアップが必要

1. Botをチャンネルに招待する
2. `ADMIN_USER_ID_LIST` で指定したユーザーで `/redmine_register_api_key [RedmineのAPIキー]` と入力し、そのチャンネルで使用するAPIキーを登録する

## その他
- `/redmine_list_registered_api_key` でAPIキーが登録されているチャンネルと紐づいているAPIキー一覧が表示できる
- `ADMIN_USER_ID_LIST` で指定したユーザーで `/redmine_register_api_key` と入力するとそのチャンネルに紐づくAPIキーを削除することが出来る
- チャンネルがアクセスできるプロジェクトの範囲の制御はそのチャンネルに登録するAPIキーにより制御する設計
    - チャンネルAでプロジェクト1のチケットを表示したいけどそれ以外のプロジェクトを表示したくないという場合は、プロジェクト1のみのアクセス権を持つユーザーのAPIキーをチャンネルAに登録すればよい、ということ
