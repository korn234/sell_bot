import discord
import random
import requests
import os
from discord.ext import commands
from discord.ui import Button, View, Select

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
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
        return daily_keys[duration].pop(0)
    elif duration in season_keys and season_keys[duration]:
        return season_keys[duration].pop(0)
    return None


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

            def __init__(self, price, duration):
                super().__init__()
                self.price = price
                self.duration = duration

            @discord.ui.button(label="✅ ยืนยันการโอนเงิน",
                               style=discord.ButtonStyle.green)
            async def confirm_payment(self, interaction: discord.Interaction,
                                      button: discord.ui.Button):
                try:
                    # First, send initial response
                    await interaction.response.send_message("⌛ กำลังดำเนินการ...", ephemeral=True)

                    # Assign roles based on purchase amount
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

                    # Initialize success_msg before using it
                    success_msg = None

                    try:
                    # Send product details and video based on price
                        key = get_next_key(self.duration)
                        if not key:
                            await interaction.followup.send("❌ ขออภัย ไม่มีคีย์เหลือในระบบ กรุณาติดต่อแอดมิน", ephemeral=True)
                            return

                        if self.price in [99, 190, 300, 799]:  
                    # Daily prices
                            video_url = "https://cdn.discordapp.com/attachments/1357266173435056169/1357385840484946122/7F0D9946-E139-4D0E-B7C8-FD67EF2825ED.mov?ex=67f00393&is=67eeb213&hm=2feb59c6e2ed4783f9be4c42e92bd0f5ec34615dc80b265adf838f969aa7681a&"
                            product_embed = discord.Embed(
                                title="🎮 รายละเอียดสินค้า",
                                description=f"ขอบคุณสำหรับการสั่งซื้อ!\n\n"
                                "**ตัวเกม 🎮**\n"
                                "https://install.appcenter.ms/users/nexus2004x-gmail.com/apps/savage-ss2025/distribution_groups/2025\n\n"
                                f"**คีย์ใช้งาน ({self.duration})**\n"
                                f"```\n{key}\n```",
                                color=discord.Color.gold())
                            await channel.send(f"🎥 วิดีโอตัวอย่าง: {video_url}")
                            success_msg = await interaction.followup.send("✅ ส่งข้อมูลสินค้าและวิดีโอให้คุณทาง DM แล้ว!")
                        else: 
                            # Season prices
                                    # similar block for handling season prices...
                            key = get_next_key(self.duration)
                            if not key:
                                await interaction.followup.send("❌ ขออภัย ไม่มีคีย์เหลือในระบบ กรุณาติดต่อแอดมิน", ephemeral=True)
                                return

                            video_url = "https://cdn.discordapp.com/attachments/1346020615798259722/1346020719317880863/RPReplay_Final1740986629.mov?ex=67ef897b&is=67ee37fb&hm=ca0890509058b8f4e666d6c35d003862a2adbd21307b9f8866c41f89d823702e&"
                            product_embed = discord.Embed(
                                title="🎮 รายละเอียดสินค้า",
                                description=f"ขอบคุณสำหรับการสั่งซื้อ!\n\n"
                                "**DNS กันดำ ☣️**\n"
                                "https://khoindvn.io.vn/document/DNS/khoindns.mobileconfig?sign=1\n\n"
                                "**ตัวเกม 🎮**\n"
                                "https://install.appcenter.ms/users/rovvipxcheat/apps/rov-fullfuntion/distribution_groups/rov\n\n"
                                f"**คีย์ใช้งาน ({self.duration})**\n"
                                f"```\n{key}\n```",
                                color=discord.Color.gold())
                            await channel.send(f"🎥 วิดีโอตัวอย่าง: {video_url}")
                            success_msg = await interaction.followup.send("✅ ส่งข้อมูลสินค้าและวิดีโอให้คุณทาง DM แล้ว!")
                        await interaction.user.send(embed=product_embed)
                        #await interaction.edit_original_response(content="✅ ส่งข้อมูลสินค้าและวิดีโอให้คุณทาง DM แล้ว!")
                        
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
                    await success_msg.edit(content="✅ ส่งข้อมูลสินค้าและวิดีโอให้คุณทาง DM แล้ว!")
                except discord.HTTPException as e:
                    await interaction.followup.send(
                        "❌ เกิดข้อผิดพลาด: ไม่สามารถส่งข้อความได้ กรุณาลองใหม่อีกครั้ง",
                        ephemeral=True)
                except Exception as e:
                    await interaction.followup.send(
                        f"❌ เกิดข้อผิดพลาด: {str(e)}", ephemeral=True)

        confirm_view = ConfirmPaymentView(self.price, self.duration)
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
        channel = await interaction.guild.create_text_channel(
            channel_name,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🎫 ช่องทางติดต่อแอดมิน",
            description=f"👋 สวัสดี {interaction.user.mention}!\n\n✍️ สามารถพิมพ์ข้อความที่ต้องการสอบถามได้เลยครับ\nแอดมินจะรีบตอบกลับโดยเร็วที่สุด",
            color=discord.Color.blue()
        )

        view = View()
        view.add_item(CloseButton())
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ สร้างช่องสำหรับติดต่อแอดมินแล้ว! กรุณาไปที่ {channel.mention}", ephemeral=True)

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
            title="🎮 ROV iOS PREMIUM SERVICES",
            description=(
                "# 🌟 Premium Features\n"
                "> 💯 ไม่ต้องปัดเกมตอนจบ\n"
                "> 🔒 ปลอดภัย 100%\n"
                "> 📱 ติดตั้งง่าย ใช้งานสะดวก\n"
                "> 🔄 อัพเดทสม่ำเสมอ\n"
                "> 👥 ทีมงานดูแล 24/7\n\n"
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
            title="🎮 ROV iOS PREMIUM SERVICES",
            description=(
                "# 🌟 Premium Features\n"
                "> 🛡️ ระบบป้องกันการแบน\n"
                "> 📱 ติดตั้งง่าย ใช้งานสะดวก\n"
                "> 🔄 อัพเดทสม่ำเสมอ\n"
                "> 👥 ทีมงานดูแล 24/7\n\n"
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


bot.run(TOKEN)