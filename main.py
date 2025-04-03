import os
import discord
import random
import requests
import os
from discord.ext import commands
from discord.ui import Button, View, Select

from myserver import server_on

TOKEN = os.getenv("DISCORD_TOKEN")  # ใช้ตัวแปรแวดล้อมแทน
SEASON_CHANNEL_ID = 1304398097421434930  # ช่องซีซั่น
DAILY_CHANNEL_ID = 1357307785833873589   # ช่องรายวัน

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
    "095-746-4287"
}

DAILY_PAYMENT_PAIRS = {
    "https://media.discordapp.net/attachments/1357027765794373642/1357323518127247501/New_Project_404_7B9F1CE.png?ex=67efc988&is=67ee7808&hm=c53f3c099338c8d36487fbbd075e3fdb674a3323b33c04e523be36e67fa9cce9&=&format=webp&quality=lossless&width=791&height=989": "097-206-0458"
}


class CloseButton(discord.ui.Button):

    def __init__(self):
        super().__init__(label="❌ ปิดช่องแชท", style=discord.ButtonStyle.red)

    async def callback(self, interaction: discord.Interaction):
        if isinstance(interaction.channel, discord.TextChannel):
            await interaction.channel.delete()


class ConfirmView(View):

    def __init__(self, price: int, duration: str):
        super().__init__()
        self.price = price
        self.duration = duration

    @discord.ui.button(label="✅ ยืนยัน", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction,
                      button: discord.ui.Button):
        # Create private channel
        overwrites = {
            interaction.guild.default_role:
            discord.PermissionOverwrite(read_messages=False),
            interaction.user:
            discord.PermissionOverwrite(read_messages=True,
                                        send_messages=True),
            interaction.guild.me:
            discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Add admin role permissions if it exists
        admin_role = discord.utils.get(interaction.guild.roles, name="Admin")
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True)

        channel_name = f"order-{interaction.user.name}"
        channel = await interaction.guild.create_text_channel(
            channel_name,
            overwrites=overwrites,
            topic=f"Order: {self.duration} - {self.price} บาท")

        await interaction.response.send_message(
            f"✅ สร้างห้องสำหรับการซื้อแล้ว! กรุณาไปที่ {channel.mention}",
            ephemeral=True)

        # Send initial message in the new channel
        # สุ่ม QR code และได้เบอร์วอเลทที่ตรงกัน ตามประเภทการซื้อ
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

        # Create confirmation view
        class ConfirmPaymentView(View):

            def __init__(self, price):
                super().__init__()
                self.price = price

            @discord.ui.button(label="✅ ยืนยันการโอนเงิน",
                               style=discord.ButtonStyle.green)
            async def confirm_payment(self, interaction: discord.Interaction,
                                      button: discord.ui.Button):
                try:
                    # First, acknowledge the interaction
                    await interaction.response.defer(ephemeral=True)

                    # Assign roles based on purchase amount
                    if self.price in [150, 300]:
                        role = interaction.guild.get_role(1301486981641015416)
                        if role:
                            await interaction.user.add_roles(role)
                    elif self.price == 400:
                        role1 = interaction.guild.get_role(1301486981641015416)
                        role2 = interaction.guild.get_role(1337637128410103882)
                        if role1 and role2:
                            await interaction.user.add_roles(role1, role2)

                    try:
                        # Send product details and video based on price
                        if self.price in [99, 190, 300, 799]:  # Daily prices
                            product_embed = discord.Embed(
                                title="🎮 รายละเอียดสินค้า",
                                description="ขอบคุณสำหรับการสั่งซื้อ!\n\n"
                                "**DNS กันดำ ☣️**\n"
                                "https://khoindvn.io.vn/document/DNS/khoindns.mobileconfig?sign=1\n\n"
                                "**ตัวเกม 🎮**\n"
                                "https://install.appcenter.ms/users/rovvipxcheat/apps/rov-fullfuntion/distribution_groups/rov-daily\n\n"
                                "**คีย์ใช้งาน**\n"
                                "```\nDoDEE\nDaily\n```",
                                color=discord.Color.gold())
                        else:  # Season prices
                            video_file = discord.File(
                                "attached_assets/RPReplay_Final1740986629.mov")
                            product_embed = discord.Embed(
                                title="🎮 รายละเอียดสินค้า",
                                description="ขอบคุณสำหรับการสั่งซื้อ!\n\n"
                                "**DNS กันดำ ☣️**\n"
                                "https://khoindvn.io.vn/document/DNS/khoindns.mobileconfig?sign=1\n\n"
                                "**ตัวเกม 🎮**\n"
                                "https://install.appcenter.ms/users/rovvipxcheat/apps/rov-fullfuntion/distribution_groups/rov\n\n"
                                "**คีย์ใช้งาน**\n"
                                "```\nDoDEE\nFullFuntion\n```",
                                color=discord.Color.gold())
                            await interaction.user.send(file=video_file)
                        await interaction.user.send(embed=product_embed)
                        success_msg = await interaction.followup.send(
                            "⌛ กำลังส่งข้อมูล...", ephemeral=True)
                    except discord.HTTPException as e:
                        await interaction.followup.send(
                            "❌ ไม่สามารถส่งข้อความได้: " + str(e),
                            ephemeral=True)
                        return

                    # Send notification to notification channel
                    notification_channel = interaction.guild.get_channel(
                        1357308234137866370)
                    if notification_channel:
                        notification_embed = discord.Embed(
                            title="🛍️ การสั่งซื้อใหม่!",
                            description=
                            f"👤 ผู้ซื้อ: {interaction.user.mention}\n"
                            f"🎮 แพ็คเกจ: {self.price} บาท\n"
                            f"📱 ผู้รับเงิน: {phone}\n"
                            f"⏱️ เวลา: <t:{int(discord.utils.utcnow().timestamp())}:F>",
                            color=discord.Color.green())
                        await notification_channel.send(embed=notification_embed)
                    await success_msg.edit(
                        content="✅ ส่งข้อมูลสินค้าและวิดีโอให้คุณทาง DM แล้ว!")
                except discord.HTTPException as e:
                    await interaction.followup.send(
                        "❌ เกิดข้อผิดพลาด: ไม่สามารถส่งข้อความได้ กรุณาลองใหม่อีกครั้ง",
                        ephemeral=True)
                except Exception as e:
                    await interaction.followup.send(
                        f"❌ เกิดข้อผิดพลาด: {str(e)}", ephemeral=True)

        confirm_view = ConfirmPaymentView(self.price)
        confirm_view.add_item(CloseButton())
        await channel.send(embed=embed, view=confirm_view)

        # Send payment instruction message
        payment_instruction = discord.Embed(
            title="💳 แจ้งชำระเงิน",
            description=
            f"🙏 {interaction.user.mention} รบกวนแจ้งสลิปการโอนเงินด้วยครับ\n"
            "เมื่อโอนเงินเรียบร้อยแล้ว กรุณากดปุ่มสีเขียว '✅ ยืนยันการโอนเงิน' ด้านบนเพื่อรับสินค้า",
            color=discord.Color.green())
        await channel.send(embed=payment_instruction)

    @discord.ui.button(label="❌ ยกเลิก", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction,
                     button: discord.ui.Button):
        await interaction.response.send_message("❌ ยกเลิกการสั่งซื้อแล้ว",
                                                ephemeral=True)


class SeasonPriceDropdown(Select):

    def __init__(self):
        options = [
            discord.SelectOption(label="1 ซีซั่น",
                                 description="ราคา 150 บาท",
                                 emoji="💰"),
            discord.SelectOption(label="3 ซีซั่น",
                                 description="ราคา 300 บาท",
                                 emoji="💰"),
            discord.SelectOption(label="ถาวร",
                                 description="ราคา 400 บาท",
                                 emoji="🔥"),
        ]
        super().__init__(placeholder="💵 เลือกราคาที่ต้องการ...",
                         options=options,
                         custom_id="select_season_price")

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

        embed = discord.Embed(
            title="🛒 ยืนยันการสั่งซื้อ",
            description=f"💰 ราคา: {price} บาท\n⏱️ ระยะเวลา: {duration}",
            color=discord.Color.blue())
        view = ConfirmView(price, duration)
        await interaction.response.send_message(embed=embed,
                                                view=view,
                                                ephemeral=True)


class DailyPriceDropdown(Select):

    def __init__(self):
        options = [
            discord.SelectOption(label="3 วัน",
                                 description="ราคา 99 บาท",
                                 emoji="💰"),
            discord.SelectOption(label="15 วัน",
                                 description="ราคา 190 บาท",
                                 emoji="💰"),
            discord.SelectOption(label="30 วัน",
                                 description="ราคา 300 บาท",
                                 emoji="💰"),
            discord.SelectOption(label="ถาวร",
                                 description="ราคา 799 บาท",
                                 emoji="🔥"),
        ]
        super().__init__(placeholder="💵 เลือกราคาที่ต้องการ...",
                         options=options,
                         custom_id="select_daily_price")

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

        embed = discord.Embed(
            title="🛒 ยืนยันการสั่งซื้อ",
            description=f"💰 ราคา: {price} บาท\n⏱️ ระยะเวลา: {duration}",
            color=discord.Color.blue())
        view = ConfirmView(price, duration)
        await interaction.response.send_message(embed=embed,
                                                view=view,
                                                ephemeral=True)


class SeasonView(View):

    def __init__(self):
        super().__init__()
        self.add_item(SeasonPriceDropdown())


class DailyView(View):

    def __init__(self):
        super().__init__()
        self.add_item(DailyPriceDropdown())


@bot.event
async def on_ready():
    print(f"✅ บอท {bot.user} พร้อมทำงานแล้ว!")
    status_channel = bot.get_channel(1339360776095531078)
    if status_channel:
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
            title="『 🎮 โปร ROV iOS พร้อมให้บริการ 🎮 』",
            description="```ini\n"
                        "[ ✨ ฟีเจอร์เด่น ✨ ]\n"
                        "```\n"
                        "```yaml\n"
                        "✓ ไม่ต้องปัด    ✓ ติดตั้งง่าย\n"
                        "✓ อัพเดทตลอด    ✓ มีทีมงานดูแล\n"
                        "```\n\n"
                        "```ini\n"
                        "[ 💰 ราคาโปรโมชั่น 💰 ]\n"
                        "```\n"
                        "```css\n"
                        "• 3 วัน  : 99 บาท\n"
                        "• 15 วัน  : 190 บาท\n"
                        "• 30 วัน  : 300 บาท\n"
                        "• ถาวร  : 799 บาท\n"
                        "```",
            color=discord.Color.blue()
        )
        embed1.set_image(url="https://media.discordapp.net/attachments/1357027765794373642/1357330429429944493/New_Project_401_78BA78C.png?ex=67efcff8&is=67ee7e78&hm=b8a504a8e47ca4090bb7ccca5d960d032cd9bf014433058996dd792fafd7eb08&=&format=webp&quality=lossless&width=989&height=989")
        await daily_channel.send(embed=embed1, view=DailyView())
        
    season_channel = bot.get_channel(SEASON_CHANNEL_ID)
    if season_channel:
            embed2 = discord.Embed(
                title="『 🎮 โปร ROV iOS พร้อมให้บริการ 🎮 』",
                description="```ini\n"
                            "[ ✨ ฟีเจอร์เด่น ✨ ]\n"
                            "```\n"
                            "```yaml\n"
                            "✓ กันแบน 100%    ✓ ติดตั้งง่าย\n"
                            "✓ อัพเดทตลอด    ✓ มีทีมงานดูแล\n"
                            "```\n\n"
                            "```ini\n"
                            "[ 💰 ราคาโปรโมชั่น 💰 ]\n"
                            "```\n"
                            "```css\n"
                            "• 1 ซีซั่น  : 150 บาท\n"
                            "• 3 ซีซั่น  : 300 บาท\n"
                            "• แบบถาวร  : 400 บาท\n"
                            "```",
                color=discord.Color.blue()
            )
            embed2.set_image(url="https://media.discordapp.net/attachments/1302103738164449413/1357013189438472262/5009BB7F-C798-46C8-BAAF-BAE91B9D7D1A.jpg")
            await season_channel.send(embed=embed2, view=SeasonView())

server_on()

bot.run(os.getenv("DISCORD_TOKEN"))