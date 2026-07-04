import discord
from discord.ext import commands
from discord import app_commands
import os
from keep_alive import keep_alive

# --- Botの基本設定 ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True  # メンバーにロールを付与するために必須
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # スラッシュコマンドをDiscordサーバーに同期
        await self.tree.sync()
        print("Botが起動し、コマンドが同期されました！")

bot = MyBot()

# --- 1. 管理者用：認証パネル設置コマンド（ロールオプション付き） ---
@bot.tree.command(name="setup_panel", description="【管理者用】指定したロールを付与するボタン付き認証パネルを設置します")
@app_commands.describe(role="ボタンを押した人に付与するロールを選択してください")
@app_commands.default_permissions(administrator=True) # 管理者権限を持つ人のみ実行可能
async def setup_panel(interaction: discord.Interaction, role: discord.Role):
    # パネルの見た目（Embed）を設定
    embed = discord.Embed(
        title="✅ サーバー認証パネル",
        description=f"下の「認証する」ボタンをクリックすると、アカウントの認証が行われ、\nサーバーの参加ロール **`{role.name}`** が付与されます。",
        color=discord.Color.green()
    )
    
    # 永続的なViewを作成（timeout=None）
    view = discord.ui.View(timeout=None)
    
    # ボタンを作成。custom_id にロールIDを埋め込むのがポイントです！
    # これにより、Renderが再起動してメモリが消えても、ボタン自体がロールIDを記憶し続けます。
    button = discord.ui.Button(
        label="認証する",
        style=discord.ButtonStyle.success, # 緑色のボタン
        emoji="✅",
        custom_id=f"verify_btn_{role.id}" # 例: verify_btn_123456789012345678
    )
    view.add_item(button)
    
    # コマンドを実行した管理者にだけ見える確認メッセージ
    await interaction.response.send_message("認証パネルを設置しました。（このメッセージは他の人には見えません）", ephemeral=True)
    # 実際にチャンネルにパネルとボタンを送信
    await interaction.channel.send(embed=embed, view=view)


# --- 2. ボタンがクリックされた時のグローバル処理（再起動対策） ---
@bot.event
async def on_interaction(interaction: discord.Interaction):
    # ボタンやメニューなどのコンポーネントによる操作であるかを確認
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get("custom_id", "")
        
        # クリックされたボタンのIDが「verify_btn_」で始まっているか判定
        if custom_id.startswith("verify_btn_"):
            # ボタンIDの後ろにくっついているロールID（数字）を抽出
            role_id = int(custom_id.replace("verify_btn_", ""))
            
            # サーバー内から該当するロールと、操作したユーザーの情報を取得
            guild = interaction.guild
            role = guild.get_role(role_id)
            member = interaction.user
            
            # ロールがサーバー内に存在しない場合のエラーハンドリング
            if not role:
                await interaction.response.send_message("❌ エラー: このパネルに設定されているロールが見つかりません。", ephemeral=True)
                return
                
            try:
                # すでにロールを持っている場合は剥奪（トグル機能）、持っていない場合は付与
                if role in member.roles:
                    await member.remove_roles(role)
                    await interaction.response.send_message(f"ロールを解除しました: `{role.name}` が外されました。", ephemeral=True)
                else:
                    await member.add_roles(role)
                    await interaction.response.send_message(f"認証が成功しました！ `{role.name}` ロールを付与しました。", ephemeral=True)
                    
            except discord.Forbidden:
                # Botの権限不足エラー
                await interaction.response.send_message("❌ エラー: Botにロールを管理する権限がありません。サーバー設定でBotのロール順位を付与したいロールより上に上げてください。", ephemeral=True)
            except Exception as e:
                # その他の予期せぬエラー
                await interaction.response.send_message(f"❌ エラーが発生しました: {e}", ephemeral=True)

# --- Bot起動 ---
keep_alive()

TOKEN = os.environ.get("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("エラー: DISCORD_TOKENが設定されていません。")
