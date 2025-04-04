import discord
import random
import requests
import os
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import Button, View, Select
import threading
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")
SEASON_CHANNEL_ID = 1304398097421434930  # ช่องซีซั่น
DAILY_CHANNEL_ID = 1357307785833873589   # ช่องรายวัน
STATUS_CHANNEL_ID = 1339360776095531078

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True  # เพิ่ม intents สำหรับการจัดการสมาชิก
bot = commands.Bot(command_prefix="!", intents=intents)
# จับคู่ QR และเบอร์โทร 1:1
SEASON_PAYMENT_PAIRS = {
    "https://media.discordapp.net/attachments/1234805355188326432/1357251880035811329/IMG_7559.png":
    "080-781-8346",
    "https://media.discordapp.net/attachments/1234805355188326432/1357251970879983717/S__18849802.jpg":
    "095-746-4287",
    "https://media.discordapp.net/attachments/1357575468764762202/1357575512066625669/IMG_0230.jpg":
    "094-338-9674"
}

DAILY_PAYMENT_PAIRS = {
    "https://media.discordapp.net/attachments/1357027765794373642/1357323518127247501/New_Project_404_7B9F1CE.png?ex=67efc988&is=67ee7808&hm=c53f3c099338c8d36487fbbd075e3fdb674a3323b33c04e523be36e67fa9cce9&=&format=webp&quality=lossless&width=791&height=989": "097-206-0458"
}

#Keys System
season_keys = {
    "1 ซีซั่น": ["DoDEE \nFullFuntion", "DoDEE \nFullFuntion", "DoDEE \nFullFuntion", "DoDEE \nFullFuntion", "DoDEE \nFullFuntion", "DoDEE \nFullFuntion"],
    "3 ซีซั่น": ["DoDEE \nFullFuntion", "DoDEE \nFullFuntion", "DoDEE \nFullFuntion", "DoDEE \nFullFuntion", "DoDEE \nFullFuntion"],
    "ถาวร": ["DoDEE \nFullFuntion", "DoDEE \nFullFuntion", "DoDEE \nFullFuntion", "DoDEE \nFullFuntion", "DoDEE \nFullFuntion"]
}

daily_keys = {
    "3 วัน": ["iluvusavage-DYNAMIC-ALL-D4xYqH0sWkFNKgBU", "iluvusavage-DYNAMIC-ALL-GIsYWEZgp14n0x69", "iluvusavage-DYNAMIC-ALL-rjq1mdKkhv6R8SoB", "iluvusavage-DYNAMIC-ALL-iz0a6rOq2SAd8H3Y", "iluvusavage-DYNAMIC-ALL-ug8hlnosvXrpftxO"],
    "15 วัน": ["iluvusavage-DYNAMIC-ALL-zKF9Bo6UL2NnCgpY", "iluvusavage-DYNAMIC-ALL-8itU4oygCZejrHJV", "iluvusavage-DYNAMIC-ALL-zIh5osZfWBXOjAYJ", "iluvusavage-DYNAMIC-ALL-DHGzKafxvAVdSi0w", "iluvusavage-DYNAMIC-ALL-CsLzqilj3PIhGHSw"],
    "30 วัน": ["iluvusavage-DYNAMIC-ALL-ObomMdlT6nH5WKCe", "iluvusavage-DYNAMIC-ALL-2RNeEP54Yd7WCFaV", "iluvusavage-DYNAMIC-ALL-9wf2tb1ChrWl6HFU", "iluvusavage-DYNAMIC-ALL-tWaIhDNURSxFKmyX", "iluvusavage-DYNAMIC-ALL-La5HyEgBop8w2X4u"],
    "ถาวร": ["iluvusavage-DYNAMIC-ALL-gvPVOitMrR5yJlAw", "iluvusavage-DYNAMIC-ALL-VClF86O2aK5qGRLU", "iluvusavage-DYNAMIC-ALL-DniJmksRLK2hbeMF", "iluvusavage-DYNAMIC-ALL-0nchdDy1pXVwTqiS", "iluvusavage-DYNAMIC-ALL-0zQEgLfkdRv3OAZS"]
}

def get_next_key(duration):
    if duration in daily_keys and daily_keys[duration]:
        if len(daily_keys[duration]) <= 3:  # แจ้งเตือนเมื่อคีย์เหลือน้อย
            notification_channel = bot.get_channel(1357308234137866370)
            if notification_channel:
                asyncio.create_task(notification_channel.send(f"⚠️ แจ้งเตือน: คีย์ {duration} เหลือน้อย ({len(daily_keys[duration])} คีย์)"))
        return daily_keys[duration].pop(0)
    elif duration in season_keys and season_keys[duration]:
        if len(season_keys[duration]) <= 3:
            notification_channel = bot.get_channel(1357308234137866370)
            if notification_channel:
                asyncio.create_task(notification_channel.send(f"⚠️ แจ้งเตือน: คีย์ {duration} เหลือน้อย ({len(season_keys[duration])} คีย์)"))
        return season_keys[duration].pop(0)
    return None


# ปุ่มสำหรับปิดแชท
class CloseButton(discord.ui.Button):

    def __init__(self):
        super().__init__(label="❌ ปิดช่องแชท", style=discord.ButtonStyle.red)

    async def callback(self, interaction: discord.Interaction):
        if isinstance(interaction.channel, discord.TextChannel):
            await interaction.channel.delete()


# Class สำหรับการยืนยันการสั่งซื้อ
class ConfirmView(View):

    def __init__(self, price: int, duration: str):
        super().__init__()
        self.price = price
        self.duration = duration
        self.status_message = None

    async def update_status(self, interaction: discord.Interaction, status: str, color: discord.Color):
        embed = discord.Embed(
            title="📊 สถานะการทำรายการ",
            description=status,
            color=color
        )
        if self.status_message:
            await self.status_message.edit(embed=embed)
        else:
            self.status_message = await interaction.channel.send(embed=embed)

    @discord.ui.button(label="✅ ยืนยัน", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Create private channel
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Add admin role permissions if it exists
        admin_role = discord.utils.get(interaction.guild.roles, name="Admin")
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel_name = f"order-{interaction.user.name}"
        channel = await interaction.guild.create_text_channel(channel_name, overwrites=overwrites, topic=f"Order: {self.duration} - {self.price} บาท")

        await interaction.response.send_message(f"✅ สร้างห้องสำหรับการซื้อแล้ว! กรุณาไปที่ {channel.mention}", ephemeral=True)

        # สุ่ม QR code และได้เบอร์วอเลทที่ตรงกัน
        if self.duration in ["3 วัน", "15 วัน", "30 วัน", "ถาวร"] and self.price in [99, 190, 300, 799]:  # ราคาแบบรายวัน
            qr_url = random.choice(list(DAILY_PAYMENT_PAIRS.keys()))
            phone = DAILY_PAYMENT_PAIRS[qr_url]
        else:  # ราคาแบบรายซีซั่น
            qr_url = random.choice(list(SEASON_PAYMENT_PAIRS.keys()))
            phone = SEASON_PAYMENT_PAIRS[qr_url]

        embed = discord.Embed(
            title="📋 รายละเอียดการสั่งซื้อ",
            description=f"👋 สวัสดี {interaction.user.mention}!\n"
                        f"🛒 รายการสั่งซื้อ: {self.duration}\n"
                        f"💰 ราคา: {self.price} บาท\n"
                        f"📱 เบอร์วอเลท: {phone}\n\n"
                        "กรุณาสแกน QR Code ด้านล่างเพื่อชำระเงิน",
            color=discord.Color.blue())
        embed.set_image(url=qr_url)

        class ConfirmPaymentView(View):

            def __init__(self, price, duration):
                super().__init__()
                self.price = price
                self.duration = duration

            @discord.ui.button(label="✅ ยืนยันการโอนเงิน", style=discord.ButtonStyle.green)
            async def confirm_payment(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.view.update_status(interaction, "⌛ กำลังตรวจสอบการชำระเงิน...", discord.Color.gold())
                def check_payment(message):
                    return message.author == interaction.user and message.channel == interaction.channel and message.attachments

                await interaction.response.send_message("📎 กรุณาส่งสลิปการโอนเงินภายใน 5 นาที", ephemeral=True)

                try:
                    payment_msg = await bot.wait_for('message', check=check_payment, timeout=300)
                    if not payment_msg.attachments:
                        await self.view.update_status(interaction, "❌ ไม่พบสลิปการโอนเงิน กรุณาลองใหม่อีกครั้ง", discord.Color.red())
                        return
                except TimeoutError:
                    await self.view.update_status(interaction, "⏰ หมดเวลาส่งสลิป กรุณาทำรายการใหม่", discord.Color.red())
                    return

                # Logic for assigning roles and sending product details
                # Your existing code for processing payment and sending product keys
                await interaction.user.send(embed=product_embed)

            @discord.ui.button(label="❌ ยกเลิกการชำระเงิน", style=discord.ButtonStyle.red)
            async def cancel_payment(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.view.update_status(interaction, "🚫 ยกเลิกการทำรายการแล้ว", discord.Color.red())
                await interaction.response.send_message("❌ ยกเลิกการชำระเงินแล้ว", ephemeral=True)
                await asyncio.sleep(5)
                if isinstance(interaction.channel, discord.TextChannel):
                    await interaction.channel.delete()

        confirm_view = ConfirmPaymentView(self.price, self.duration)
        confirm_view.view = self  # Assign self to the inner view for access to update_status
        confirm_view.add_item(CloseButton())
        await channel.send(embed=embed, view=confirm_view)

        # Send payment instruction message
        payment_instruction = discord.Embed(
            title="💳 แจ้งชำระเงิน",
            description=f"🙏 {interaction.user.mention} รบกวนแจ้งสลิปการโอนเงินด้วยครับ\n"
                        "เมื่อโอนเงินเรียบร้อยแล้ว กรุณากดปุ่มสีเขียว '✅ ยืนยันการโอนเงิน' ด้านบนเพื่อรับสินค้า",
            color=discord.Color.green())
        await channel.send(embed=payment_instruction)

    @discord.ui.button(label="❌ ยกเลิก", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("❌ ยกเลิกการสั่งซื้อแล้ว", ephemeral=True)


# View สำหรับการเลือกซื้อซีซั่น
class SeasonPriceDropdown(Select):

    def __init__(self):
        options = [
            discord.SelectOption(label="1 ซีซั่น", description="ราคา 150 บาท", emoji="💰"),
            discord.SelectOption(label="3 ซีซั่น", description="ราคา 300 บาท", emoji="💰"),
            discord.SelectOption(label="ถาวร", description="ราคา 400 บาท", emoji="🔥"),
        ]
        super().__init__(placeholder="💵 เลือกราคาที่ต้องการ...", options=options, custom_id="select_season_price")

    async def callback(self, interaction: discord.Interaction):
        selection = self.values[0]
        if selection == "1 ซีซั่น":
            price = 150
            duration = "1 ซีซั่น"
        elif selection == "3 ซีซั่น":
            price = 300
            duration = "3 ซีซั่น"
        else:
            price = 400
            duration = "ถาวร"

        embed = discord.Embed(title="🛒 ยืนยันการสั่งซื้อ", description=f"💰 ราคา: {price} บาท\n⏱️ ระยะเวลา: {duration}", color=discord.Color.blue())
        view = ConfirmView(price, duration)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# View สำหรับการเลือกซื้อรายวัน
class DailyPriceDropdown(Select):

    def __init__(self):
        options = [
            discord.SelectOption(label="3 วัน", description="ราคา 99 บาท", emoji="💰"),
            discord.SelectOption(label="15 วัน", description="ราคา 190 บาท", emoji="💰"),
            discord.SelectOption(label="30 วัน", description="ราคา 300 บาท", emoji="💰"),
            discord.SelectOption(label="ถาวร", description="ราคา 799 บาท", emoji="🔥"),
        ]
        super().__init__(placeholder="💵 เลือกราคาที่ต้องการ...", options=options, custom_id="select_daily_price")

    async def callback(self, interaction: discord.Interaction):
        selection = self.values[0]
        if selection == "3 วัน":
            price = 99
            duration = "3 วัน"
        elif selection == "15 วัน":
            price = 190
            duration = "15 วัน"
        elif selection == "30 วัน":
            price = 300
            duration = "30 วัน"
        else:
            price = 799
            duration = "ถาวร"

        embed = discord.Embed(title="🛒 ยืนยันการสั่งซื้อ", description=f"💰 ราคา: {price} บาท\n⏱️ ระยะเวลา: {duration}", color=discord.Color.blue())
        view = ConfirmView(price, duration)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class AdminContactButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="👨‍💼 ติดต่อแอดมิน", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        admin_role = discord.utils.get(interaction.guild.roles, name="Admin")
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel_name = f"support-{interaction.user.name}"
        channel = await interaction.guild.create_text_channel(channel_name, overwrites=overwrites)

        embed = discord.Embed(
            title="📬 ติดต่อแอดมิน",
            description="ยินดีต้อนรับ! หากคุณมีคำถามหรือปัญหาทางระบบ กรุณาส่งข้อความมาที่นี่",
            color=discord.Color.blue())
        await channel.send(embed=embed)

        # เพิ่มปุ่ม "ปิดช่องแชท"
        close_button = CloseButton()
        await channel.send("🔒 หากต้องการปิดแชทนี้ กรุณากดปุ่มด้านล่าง", view=View().add_item(close_button))

        await interaction.response.send_message(f"📬 สร้างช่องแชทส่วนตัวเรียบร้อยแล้ว! กรุณาไปที่ {channel.mention}", ephemeral=True)

class SeasonView(View):
    def __init__(self):
        super().__init__()
        self.add_item(SeasonPriceDropdown())
        self.add_item(AdminContactButton())

class DailyView(View):
    def __init__(self):
        super().__init__()
        self.add_item(DailyPriceDropdown())
        self.add_item(AdminContactButton())

@bot.event
async def on_ready():
    print(f"✅ บอท {bot.user} พร้อมทำงานแล้ว!")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการซิงค์คำสั่ง: {e}")

    clear_and_post.start()

# ฟังก์ชันลบข้อความทั้งหมดก่อนโพสต์ใหม่
async def clear_channels():
    channels = [
        bot.get_channel(DAILY_CHANNEL_ID),
        bot.get_channel(SEASON_CHANNEL_ID),
        bot.get_channel(STATUS_CHANNEL_ID),
    ]

    for channel in channels:
        if channel:
            try:
                await channel.purge()
                print(f"✅ ลบข้อความใน {channel.name} สำเร็จ!")
            except Exception as e:
                print(f"❌ ลบข้อความใน {channel.name} ไม่สำเร็จ: {e}")

# ฟังก์ชันโพสต์ข้อความใหม่
async def post_messages():
    status_channel = bot.get_channel(STATUS_CHANNEL_ID)
    if status_channel:
        try:
            response = requests.get('http://0.0.0.0:5000/')
            status = "🟢 ระบบทำงานปกติ" if response.status_code == 200 else "🔴 ระบบมีปัญหา"
            await bot.change_presence(status=discord.Status.online if response.status_code == 200 else discord.Status.dnd, activity=discord.Game(name=status))
            if response.status_code != 200:
                await status_channel.send("⚠️ แจ้งเตือน: ระบบมีปัญหา กรุณาตรวจสอบ")
        except Exception as e:
            await status_channel.send(f"❌ เกิดข้อผิดพลาดในการเช็คสถานะ: {str(e)}")

        status_message = ("```ini\n"
                          "[ 🎮 สถานะโปรแกรมและเกม 🎮 ]\n"
                          "```\n"
                          "**📊 สถานะการให้บริการ**\n"
                          "```yaml\n"
                          "🟢 พร้อมใช้งาน   | ระบบทำงานปกติ\n"
                          "🟡 กำลังแก้ไข    | อยู่ระหว่างปรับปรุง\n"
                          "🔴 ไม่พร้อมใช้งาน | ระบบปิดปรับปรุง\n"
                          "```\n"
                          "**📱 สถานะเกม**\n"
                          "```css\n"
                          "• ROV iOS (รายซีซั่น/ถาวร)  🟡\n"
                          "• ROV iOS (รายวัน/รายซีซั่น) 🟢\n"
                          "• ROV Android           🟢\n"
                          "• Free Fire             🟢\n"
                          "• 8 Ball Pool           🟢\n"
                          "```")
        await status_channel.send(status_message)

    daily_channel = bot.get_channel(DAILY_CHANNEL_ID)
    if daily_channel:
        embed1 = discord.Embed(
            title="⚔️ ROV iOS PREMIUM SERVICES ⚔️",
            description=(
                "# 🌟 Premium Features\n"
                "> 🎯 ไม่ต้องปัดเกมตอนจบ\n"
                "> 🛡️ ปลอดภัย 100%\n"
                "> 📲 ติดตั้งง่าย ใช้งานสะดวก\n"
                "> ⚡ อัพเดทสม่ำเสมอ\n"
                "> 🔰 ทีมงานดูแล 24/7\n\n"
                "# 💎 ราคาแพ็คเกจรายวัน\n"
                "```md\n"
                "# 3 วัน\n"
                "* ราคา 99 บาท\n\n"
                "# 15 วัน\n"
                "* ราคา 190 บาท\n\n"
                "# 30 วัน\n"
                "* ราคา 300 บาท\n\n"
                "# แบบถาวร\n"
                "* ราคา 799 บาท\n"
                "```"
            ),
            color=0x2ecc71
        )
        embed1.set_thumbnail(url="https://media.discordapp.net/attachments/1357027765794373642/1357330429429944493/New_Project_401_78BA78C.png")
        embed1.set_footer(text="✨ เลือกแพ็คเกจด้านล่างเพื่อสั่งซื้อ", icon_url="https://media.discordapp.net/attachments/1357027765794373642/1357330429429944493/New_Project_401_78BA78C.png")
        await daily_channel.send(embed=embed1, view=DailyView())

    season_channel = bot.get_channel(SEASON_CHANNEL_ID)
    if season_channel:
        embed2 = discord.Embed(
            title="⚔️ ROV iOS PREMIUM SERVICES ⚔️",
            description=(
                "# 🌟 Premium Features\n"
                "> 🛡️ ระบบป้องกันการแบน\n"
                "> 📲 ติดตั้งง่าย ใช้งานสะดวก\n"
                "> ⚡ อัพเดทสม่ำเสมอ\n"
                "> 🔰 ทีมงานดูแล 24/7\n\n"
                "# 💎 ราคาแพ็คเกจรายซีซั่น\n"
                "```md\n"
                "# 1 ซีซั่น\n"
                "* ราคา 150 บาท\n\n"
                "# 3 ซีซั่น\n"
                "* ราคา 300 บาท\n\n"
                "# แบบถาวร\n"
                "* ราคา 400 บาท\n"
                "```"
            ),
            color=0x2ecc71
        )
        embed2.set_thumbnail(url="https://media.discordapp.net/attachments/1302103738164449413/1357013189438472262/5009BB7F-C798-46C8-BAAF-BAE91B9D7D1A.jpg")
        embed2.set_footer(text="✨ เลือกแพ็คเกจด้านล่างเพื่อสั่งซื้อ", icon_url="https://media.discordapp.net/attachments/1302103738164449413/1357013189438472262/5009BB7F-C798-46C8-BAAF-BAE91B9D7D1A.jpg")
        await season_channel.send(embed=embed2, view=SeasonView())

# Task ลบข้อความและโพสต์ใหม่ทุก 3 นาที
@tasks.loop(minutes=5)
async def clear_and_post():
    await clear_channels()
    await post_messages()

@bot.tree.command(name="add", description="เพิ่มคีย์ใหม่ (Admin only)")
@app_commands.choices(type=[
    app_commands.Choice(name="Day", value="day"),
    app_commands.Choice(name="Season", value="season")
])
@app_commands.choices(duration=[
    app_commands.Choice(name="3 วัน", value="3 วัน"),
    app_commands.Choice(name="15 วัน", value="15 วัน"),
    app_commands.Choice(name="30 วัน", value="30 วัน"),
    app_commands.Choice(name="ถาวร", value="ถาวร"),
    app_commands.Choice(name="1 ซีซั่น", value="1 ซีซั่น"),
    app_commands.Choice(name="3 ซีซั่น", value="3 ซีซั่น")
])
async def add_key(interaction: discord.Interaction, type: str, duration: str, key: str):
    if not any(role.name == "Admin" for role in interaction.user.roles):
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้", ephemeral=True)
        return

    if type == "day" and duration in daily_keys:
        daily_keys[duration].append(key)
        await interaction.response.send_message(f"✅ เพิ่มคีย์สำหรับ {duration} เรียบร้อยแล้ว", ephemeral=True)
    elif type == "season" and duration in season_keys:
        season_keys[duration].append(key)
        await interaction.response.send_message(f"✅ เพิ่มคีย์สำหรับ {duration} เรียบร้อยแล้ว", ephemeral=True)
    else:
        await interaction.response.send_message("❌ ไม่พบระยะเวลาที่ระบุ", ephemeral=True)

@bot.tree.command(name="remove", description="ลบคีย์ (Admin only)")
@app_commands.choices(type=[
    app_commands.Choice(name="Day", value="day"),
    app_commands.Choice(name="Season", value="season")
])
@app_commands.choices(duration=[
    app_commands.Choice(name="3 วัน", value="3 วัน"),
    app_commands.Choice(name="15 วัน", value="15 วัน"),
    app_commands.Choice(name="30 วัน", value="30 วัน"),
    app_commands.Choice(name="ถาวร", value="ถาวร"),
    app_commands.Choice(name="1 ซีซั่น", value="1 ซีซั่น"),
    app_commands.Choice(name="3 ซีซั่น", value="3 ซีซั่น")
])
async def remove_key(interaction: discord.Interaction, type: str, duration: str, key: str):
    if not any(role.name == "Admin" for role in interaction.user.roles):
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้", ephemeral=True)
        return

    if type == "day" and duration in daily_keys and key in daily_keys[duration]:
        daily_keys[duration].remove(key)
        await interaction.response.send_message(f"✅ ลบคีย์สำหรับ {duration} เรียบร้อยแล้ว", ephemeral=True)
    elif type == "season" and duration in season_keys and key in season_keys[duration]:
        season_keys[duration].remove(key)
        await interaction.response.send_message(f"✅ ลบคีย์สำหรับ {duration} เรียบร้อยแล้ว", ephemeral=True)
    else:
        await interaction.response.send_message("❌ ไม่พบคีย์ที่ระบุ", ephemeral=True)

@bot.tree.command(name="list", description="แสดงรายการคีย์ทั้งหมด (Admin only)")
@app_commands.choices(type=[
    app_commands.Choice(name="Day", value="day"),
    app_commands.Choice(name="Season", value="season")
])
@app_commands.choices(duration=[
    app_commands.Choice(name="3 วัน", value="3 วัน"),
    app_commands.Choice(name="15 วัน", value="15 วัน"),
    app_commands.Choice(name="30 วัน", value="30 วัน"),
    app_commands.Choice(name="ถาวร", value="ถาวร"),
    app_commands.Choice(name="1 ซีซั่น", value="1 ซีซั่น"),
    app_commands.Choice(name="3 ซีซั่น", value="3 ซีซั่น")
])
async def list_keys(interaction: discord.Interaction, type: str, duration: str):
    if not any(role.name == "Admin" for role in interaction.user.roles):
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้", ephemeral=True)
        return

    if type == "day" and duration in daily_keys:
        keys = daily_keys[duration]
        await interaction.response.send_message(f"🔑 คีย์สำหรับ {duration}:\n```\n" + "\n".join(keys) + "\n```", ephemeral=True)
    elif type == "season" and duration in season_keys:
        keys = season_keys[duration]
        await interaction.response.send_message(f"🔑 คีย์สำหรับ {duration}:\n```\n" + "\n".join(keys) + "\n```", ephemeral=True)
    else:
        await interaction.response.send_message("❌ ไม่พบระยะเวลาที่ระบุ", ephemeral=True)

@bot.command(name="announce")
@commands.has_role("Admin")
async def text_announce(ctx, *, message):
    """ประกาศข้อความ (Admin only)"""
    await ctx.message.delete()
    embed = discord.Embed(
        title="📢 ประกาศ",
        description=message,
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"ประกาศโดย {ctx.author.name}")
    await ctx.send(embed=embed)

@bot.tree.command(name="announce", description="ประกาศข้อความ (Admin only)")
async def slash_announce(interaction: discord.Interaction, message: str):
    if not any(role.name == "Admin" for role in interaction.user.roles):
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้", ephemeral=True)
        return

    embed = discord.Embed(
        title="📢 ประกาศ",
        description=message,
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"ประกาศโดย {interaction.user.name}")
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    # ระบบตอบคำถามอัตโนมัติ
    faq = {
        "ราคา": "💰 ราคาแพ็คเกจ:\n- รายวัน: 99-799 บาท\n- รายซีซั่น: 150-400 บาท",
        "วิธีติดตั้ง": "📱 วิธีติดตั้ง:\n1. ติดตั้ง DNS\n2. ติดตั้งแอพ\n3. ใส่คีย์ที่ได้รับ",
        "ช่องทางชำระเงิน": "💳 ช่องทางชำระเงิน:\n- True Wallet\n- โอนผ่านธนาคาร",
        "ติดต่อแอดมิน": "👨‍💼 กดปุ่ม 'ติดต่อแอดมิน' ในช่องสั่งซื้อได้เลยครับ"
    }

    for keyword, response in faq.items():
        if keyword in message.content.lower():
            await message.reply(response)
            break

    await bot.process_commands(message)

if __name__ == "__main__":
    from myserver import run_server
    import threading
    server_thread = threading.Thread(target=run_server)
    server_thread.start()
    bot.run(TOKEN)
