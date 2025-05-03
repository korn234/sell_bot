import discord
import random
import requests
import os
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import Button, View, Select
from dotenv import load_dotenv
import threading
import asyncio
from discord import Interaction
from discord.ui import Button, View
from discord import Embed, ButtonStyle
import asyncio
import random
import aiohttp
from datetime import datetime, timedelta
import pytz

# โหลดค่าในไฟล์ .env
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def create_gist(content):
    url = "https://api.github.com/gists"
    payload = {
        "description": "Key for DoDEE",
        "public": False,
        "files": {
            "key.txt": {
                "content": content
            }
        }
    }

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 201:
            return response.json()["html_url"]
        else:
            print(f"❌ สร้าง Gist ไม่สำเร็จ: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการสร้าง Gist: {e}")
        return None

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
# Format: (QR URL, Phone number, probability weight)
SEASON_PAYMENT_OPTIONS = [
    ("https://media.discordapp.net/attachments/1234805355188326432/1357251880035811329/IMG_7559.png", "080-781-8346", 90),
    ("https://media.discordapp.net/attachments/1234805355188326432/1357251970879983717/S__18849802.jpg", "095-746-4287", 0),
    ("https://media.discordapp.net/attachments/1234805355188326432/1358795179414392973/IMG_7604.jpg?ex=67f5241f&is=67f3d29f&hm=919cdde082227255e674acea218d36bb904c1e92b93b5cdb0f9e66dbd1112654&=&format=webp&width=456&height=988", "094-338-9674", 10)
]

DAILY_PAYMENT_PAIRS = {
    "https://media.discordapp.net/attachments/1357027765794373642/1357323518127247501/New_Project_404_7B9F1CE.png?ex=67efc988&is=67ee7808&hm=c53f3c099338c8d36487fbbd075e3fdb674a3323b33c04e523be36e67fa9cce9&=&format=webp&quality=lossless&width=791&height=989": "097-206-0458"
}

import json
import os

# Load keys from files or create empty if not exists
def load_keys():
    if os.path.exists('season_keys.json'):
        with open('season_keys.json', 'r') as f:
            return json.load(f)
    return {
        "1 ซีซั่น": [],
        "3 ซีซั่น": [],
        "ถาวร": []
    }

def load_daily_keys():
    if os.path.exists('daily_keys.json'):
        with open('daily_keys.json', 'r') as f:
            return json.load(f)
    return {
        "3 วัน": [],
        "15 วัน": [],
        "30 วัน": [],
        "ถาวร": []
    }

# Save keys to files
def save_keys():
    with open('season_keys.json', 'w') as f:
        json.dump(season_keys, f, indent=4)

def save_daily_keys():
    with open('daily_keys.json', 'w') as f:
        json.dump(daily_keys, f, indent=4)

season_keys = load_keys()
daily_keys = load_daily_keys()

def get_next_key(duration, type=None):
    keys = None

    if type == "daily":
        if duration in daily_keys and daily_keys[duration]:
            keys = daily_keys[duration]
    elif type == "season":
        if duration in season_keys and season_keys[duration]:
            keys = season_keys[duration]
    else:
        # fallback แบบเดิม
        if duration in daily_keys and daily_keys[duration]:
            keys = daily_keys[duration]
        elif duration in season_keys and season_keys[duration]:
            keys = season_keys[duration]

    if keys and len(keys) > 0:
        if len(keys) <= 3:  # แจ้งเตือนเมื่อคีย์เหลือน้อย
            notification_channel = bot.get_channel(1357308234137866370)
            if notification_channel:
                asyncio.create_task(
                    notification_channel.send(
                        f"⚠️ แจ้งเตือน: คีย์ {duration} เหลือน้อย ({len(keys)} คีย์)"
                    )
                )
        return keys[0]  # ส่งคีย์แรกคืน แต่ยังไม่ลบ

    return None

def remove_used_key(duration, key):
    if duration in daily_keys and key in daily_keys[duration]:
        daily_keys[duration].remove(key)
        save_daily_keys()
        return True
    elif duration in season_keys and key in season_keys[duration]:
        season_keys[duration].remove(key)
        save_keys()
        return True
    return False


class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="❌ ปิดช่องแชท", style=discord.ButtonStyle.red, custom_id="close_button")

    async def callback(self, interaction: discord.Interaction):
        if isinstance(interaction.channel, discord.TextChannel):
            await interaction.channel.delete()

class PersistentView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CloseButton())

# Store active views
active_views = {}

# เพิ่มตัวแปรเก็บยอดขาย ใส่ต่อจากการ import
daily_sales = 0  # ยอดขายเริ่มต้น

# เพิ่มฟังก์ชันอัพเดทยอดขาย
async def update_sales(amount: int):
    global daily_sales
    daily_sales += amount

# เพิ่มระบบรีเซ็ตยอดขายรายวัน
@tasks.loop(hours=24)
async def reset_daily_sales():
    global daily_sales
    daily_sales = 0
    print("✅ รีเซ็ตยอดขายรายวันแล้ว")

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
        
        try:
            if self.status_message:
                await self.status_message.edit(embed=embed)
            else:
                self.status_message = await interaction.channel.send(embed=embed)
        except Exception as e:
            # ถ้าไม่สามารถแก้ไขข้อความเดิมได้ ให้ส่งข้อความใหม่
            try:
                self.status_message = await interaction.channel.send(embed=embed)
            except Exception as e:
                print(f"❌ ไม่สามารถส่งข้อความสถานะได้: {e}")

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
            total_weight = sum(weight for _, _, weight in SEASON_PAYMENT_OPTIONS)
            r = random.uniform(0, total_weight)
            for qr, ph, weight in SEASON_PAYMENT_OPTIONS:
                r -= weight
                if r <= 0:
                    qr_url = qr
                    phone = ph
                    break

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
                await self.view.update_status(interaction, "⌛ กำลังตรวจสอบการชำระเงิน...", discord.Color.gold())
                # ตรวจสอบสลิปการโอนเงิน
                def check_payment(message):
                    return message.author == interaction.user and message.channel == interaction.channel and len(message.attachments) > 0

                await interaction.response.send_message("📎 กรุณาส่งสลิปการโอนเงินภายใน 5 นาที", ephemeral=True)

                try:
                    payment_msg = await bot.wait_for('message', check=check_payment, timeout=300)
                    # เมื่อมีการชำระเงิน อัพเดทยอดขาย
                    await update_sales(self.price)
                    # มีรูปภาพถูกส่งมา ถือว่าชำระเงินแล้ว
                    await interaction.channel.send("✅ ตรวจสอบการชำระเงินเรียบร้อย")
                except TimeoutError:
                    await interaction.channel.send("⏰ หมดเวลาส่งสลิป กรุณาทำรายการใหม่")
                    return
                try:

                    # Assign roles based on purchase amount
                    if self.price in [150, 300]:
                        role = interaction.guild.get_role(1364253774977175652)
                        if role:
                            await interaction.user.add_roles(role)
                    elif self.price == 400:
                        role1 = interaction.guild.get_role(1364253774977175652)
                        role2 = interaction.guild.get_role(1337637128410103882)
                        if role1 and role2:
                            await interaction.user.add_roles(role1, role2)

                    # Initialize success_msg before using it
                    try:
                        # Send initial success message
                        success_msg = await interaction.channel.send("⌛ กำลังดำเนินการ...")

                        # Send product details and video based on price
                        key = get_next_key(self.duration)
                        if not key:
                            await self.view.update_status(interaction, "❌ ขออภัย ไม่มีคีย์เหลือในระบบ กรุณาติดต่อแอดมิน", discord.Color.red())
                            await interaction.followup.send("❌ ขออภัย ไม่มีคีย์เหลือในระบบ กรุณาติดต่อแอดมิน", ephemeral=True)
                            return

                        if self.price in [99, 190, 300, 799]:
                            # ใช้ daily_keys
                            key = get_next_key(self.duration, type="daily")
                        else:
                            # ใช้ season_keys
                            key = get_next_key(self.duration, type="season")

                        # ---------- โค้ดส่งคีย์หลัก ----------
                        if self.price in [99, 190, 300, 799]:
                            # Daily prices
                            if key in daily_keys[self.duration]:
                                daily_keys[self.duration].remove(key)
                                save_daily_keys()
                                print(f"✅ ลบคีย์ {key} สำหรับ {self.duration} เรียบร้อยแล้ว")
                            else:
                                print(f"❌ ไม่สามารถลบคีย์ {key} สำหรับ {self.duration} ได้")

                            video_url_1 = "https://cdn.discordapp.com/attachments/1301468241335681024/1367358302106816533/IMG_0300.MP4?ex=68144b27&is=6812f9a7&hm=c64bf66043f2605dbcf57dc3956abc566edd6050c7a61d7da7676dbfcc1d6280&"
                            video_url_2 = "https://cdn.discordapp.com/attachments/1357308234137866370/1357763650227535883/videoplayback.mp4?ex=67f16370&is=67f011f0&hm=105a9ded6c87d346fd5daad3d1004b891738dc5537d4101ab8465ab6e710fd56&"

                            product_embed = discord.Embed(
                                title="🎮 รายละเอียดสินค้า",
                                description=f"ขอบคุณสำหรับการสั่งซื้อ!\n\n"
                                            "**DNS กันดำ ☣️**\n"
                                            "https://wsfteam.xyz/configprofiles\n\n"
                                            "**กลุ่มอัพเดทข่าวสารโปร**\n"
                                            "https://t.me/savageios\n\n"
                                            "**ตัวเกม 🎮**\n"
                                            "เข้าเทเลแกรมไปโหลด\n\n https://t.me/savageios\n\n"
                                            f"**คีย์ใช้งาน ({self.duration})**\n"
                                            f"```\n{key}\n```",
                                color=discord.Color.gold()
                            )

                            if self.duration == "ถาวร":
                                try:
                                    dm_channel = await interaction.user.create_dm()
                                    await dm_channel.send(
                                        "🎁 คุณได้รับสิทธิ์เข้ากลุ่มถาวร!\n\n📌 กลุ่ม Telegram:\nhttps://t.me/+ZunSLIMtyEZjODc1\n\n🛡️ **กลุ่มถาวร** ใช้งานได้ตลอดชีพ/n"
                                    )
                                except Exception as e:
                                    print(f"❌ ไม่สามารถส่ง DM กลุ่มถาวรได้: {e}")

                            dm_channel = await interaction.user.create_dm()
                            await dm_channel.send(f"🎥 วิดีโอสอนโหลด: {video_url_1}")
                            await dm_channel.send(f"🎥 วิดีโอสอนเข้าเกม: {video_url_2}")
                            await dm_channel.send(embed=product_embed)
                            await dm_channel.send("🔑 **คีย์ของคุณ:** (กดค้างคัดลอกลบ''')")
                            await dm_channel.send(content=f"```\n{key}\n```", view=HelpButtonView(key))

                        else:
                            # Season prices
                            if key in season_keys[self.duration]:
                                season_keys[self.duration].remove(key)
                                save_keys()
                                print(f"✅ ลบคีย์ {key} สำหรับ {self.duration} เรียบร้อยแล้ว")
                            else:
                                print(f"❌ ไม่สามารถลบคีย์ {key} สำหรับ {self.duration} ได้")

                            video_url = "https://cdn.discordapp.com/attachments/1301468241335681024/1368127106927558687/d1a97a74-d9dd-4f78-b55b-84bd19c24d49_transcode-out.mov?ex=68171728&is=6815c5a8&hm=7da2c5defe0b1238b0c7a43ca440e9a7658050215624d7b4a6d7a8efc9a6daa3&"

                            product_embed = discord.Embed(
                                title="🎮 รายละเอียดสินค้า",
                                description=f"ขอบคุณสำหรับการสั่งซื้อ!\n\n"
                                            "**DNS กันดำ ☣️**\n"
                                            "https://khoindvn.io.vn/document/DNS/khoindns.mobileconfig?sign=1\n\n"
                                            "**ตัวเกม 🎮**\n"
                                            "https://i.diawi.com/h714XM\n\n"
                                            f"**คีย์ใช้งาน ({self.duration})**\n"
                                            f"```\n{key}\n```",
                                color=discord.Color.gold()
                            )

                            dm_channel = await interaction.user.create_dm()
                            await dm_channel.send(f"🎥 วิดีโอตัวอย่าง: {video_url}")
                            await dm_channel.send(embed=product_embed)
                            await dm_channel.send("🔑 **คีย์ของคุณ:** (กดค้างคัดลอกลบ''')")
                            await dm_channel.send(content=f"```\n{key}\n```", view=HelpButtonView(key))
                        # Send success message in channel
                        success_msg = await self.view.update_status(interaction, "✅ ส่งข้อมูลสินค้าและวิดีโอให้คุณทาง DM แล้ว!", discord.Color.green())
                        #await interaction.edit_original_response(content="✅ ส่งข้อมูลสินค้าและวิดีโอให้คุณทาง DM แล้ว!")

                    except discord.HTTPException as e:
                        await self.view.update_status(interaction, "❌ ไม่สามารถส่งข้อความได้: " + str(e), discord.Color.red())
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
                    await self.view.update_status(interaction, "❌ เกิดข้อผิดพลาด: ไม่สามารถส่งข้อความได้ กรุณาลองใหม่อีกครั้ง", discord.Color.red())
                    await interaction.followup.send(
                        "❌ เกิดข้อผิดพลาด: ไม่สามารถส่งข้อความได้ กรุณาลองใหม่อีกครั้ง",
                        ephemeral=True)
                except Exception as e:
                    await self.view.update_status(interaction, f"❌ เกิดข้อผิดพลาด: {str(e)}", discord.Color.red())
                    await interaction.followup.send(
                        f"❌ เกิดข้อผิดพลาด: {str(e)}", ephemeral=True)

            @discord.ui.button(label="❌ ยกเลิกการชำระเงิน", style=discord.ButtonStyle.red)
            async def cancel_payment(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.view.update_status(interaction, "🚫 ยกเลิกการทำรายการแล้ว", discord.Color.red())
                await interaction.response.send_message("❌ ยกเลิกการชำระเงินแล้ว", ephemeral=True)
                await asyncio.sleep(5)
                if isinstance(interaction.channel, discord.TextChannel):
                    await interaction.channel.delete()

        confirm_view = ConfirmPaymentView(self.price, self.duration)
        confirm_view.view = self # Assign self to the inner view for access to update_status
        confirm_view.add_item(CloseButton())
        await channel.send(embed=embed, view=confirm_view)

        class CopyKeyButton(Button):
            def __init__(self, key):
                super().__init__(label="🔑 คัดลอกคีย์", style=discord.ButtonStyle.primary)
                self.key = key

            async def callback(self, interaction: discord.Interaction):
                try:
                    # เรียกฟังก์ชันสร้าง Gist โดยใช้คีย์
                    gist_url = create_gist(self.key)

                    if gist_url:
                        await interaction.response.send_message(
                            f"🔑 คุณสามารถคัดลอกคีย์ของคุณได้จากที่นี่ กดลิ้งแล้วกดคำว่า raw:\n{gist_url}",
                            ephemeral=True
                        )
                    else:
                        await interaction.response.send_message(
                            "❌ เกิดข้อผิดพลาดในการสร้างลิงก์คีย์.",
                            ephemeral=True
                        )
                except Exception as e:
                    print(f"❌ ไม่สามารถสร้างลิงก์ได้: {e}")
                    await interaction.response.send_message("❌ มีบางอย่างผิดพลาด.", ephemeral=True)

        class HelpButton(Button):
            def __init__(self):
                super().__init__(label="🛠️ มีปัญหาการติดตั้ง? กดที่นี่", style=discord.ButtonStyle.danger)

            async def callback(self, interaction: discord.Interaction):
                try:
                    await interaction.response.defer(ephemeral=True)
                    dm_channel = await interaction.user.create_dm()

                    await dm_channel.send("🌐 ลิงก์ช่วยเหลือ:\nhttps://khoindvn.io.vn/")
                    await dm_channel.send("🎥 วิดีโอสอนโหลด:\nhttps://youtube.com/shorts/N_N1EGrzd7g?si=sSx3aWixDjGv674D")
                    await dm_channel.send("🎥 วิดีโอใส่ cert + hack:\nhttps://youtube.com/shorts/G-8cYsEQnPg?si=L-MHd19qccRH5koO")
                except Exception as e:
                    print(f"❌ ไม่สามารถส่งข้อมูลช่วยเหลือได้: {e}")

        class HelpButtonView(View):
            def __init__(self, key):
                super().__init__(timeout=None)
                self.add_item(CopyKeyButton(key))
                self.add_item(HelpButton())

        # Send payment instruction message
        payment_instruction = discord.Embed(
            title="💳 แจ้งชำระเงิน",
            description=
            f"🙏 {interaction.user.mention} รบกวนแจ้งสลิปการโอนเงินด้วยครับ\n"
            "เมื่อโอนเงินเรียบร้อยแล้ว กรุณากดปุ่มสีเขียว '✅ ยืนยันการโอนเงิน' ด้านบนเพื่อรับสินค้า",
            color=discord.Color.green())
        await channel.send(embed=payment_instruction)
        await channel.send(embed=discord.Embed(
            description="✅ รอการชำระเงิน...",
            color=discord.Color.blue()
        ))
    @discord.ui.button(label="❌ ยกเลิก", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction,
                     button: discord.ui.Button):
        await interaction.response.send_message("❌ ยกเลิกการสั่งซื้อแล้ว",
                                                ephemeral=True)


class SeasonPriceDropdown(Select):

    def __init__(self):
        options = [
            discord.SelectOption(label="1 ซีซั่น",
                                 description=f"ราคา 150 บาท | เหลือ {len(season_keys['1 ซีซั่น'])} คีย์",
                                 emoji="💰"),
            discord.SelectOption(label="3 ซีซั่น",
                                 description=f"ราคา 300 บาท | เหลือ {len(season_keys['3 ซีซั่น'])} คีย์",
                                 emoji="💰"),
            discord.SelectOption(label="ถาวร",
                                 description=f"ราคา 400 บาท | เหลือ {len(season_keys['ถาวร'])} คีย์",
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
                                 description=f"ราคา 99 บาท | เหลือ {len(daily_keys['3 วัน'])} คีย์",
                                 emoji="💰"),
            discord.SelectOption(label="15 วัน",
                                 description=f"ราคา 190 บาท | เหลือ {len(daily_keys['15 วัน'])} คีย์",
                                 emoji="💰"),
            discord.SelectOption(label="30 วัน",
                                 description=f"ราคา 300 บาท | เหลือ {len(daily_keys['30 วัน'])} คีย์",
                                 emoji="💰"),
            discord.SelectOption(label="ถาวร",
                                 description=f"ราคา 799 บาท | เหลือ {len(daily_keys['ถาวร'])} คีย์",
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

        view = PersistentView()
        active_views[channel.id] = view
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ สร้างช่องสำหรับติดต่อแอดมินแล้ว! กรุณาไปที่ {channel.mention}", ephemeral=True)

class GetGameButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🎮 กดเพื่อรับตัวเกม", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        # Define the required role IDs
        required_role_ids = [1364253774977175652, 1337637128410103882]  # Replace with actual role IDs
        
        # Check if the user has at least one of the required roles
        user_roles = [role.id for role in interaction.user.roles]
        has_required_role = any(role_id in user_roles for role_id in required_role_ids)

        if has_required_role:
            # Send the game link if the user has the correct role
            game_link = "DNSกันดำ(คนไม่ไม่ได้โหลด)\n\n https://khoindvn.io.vn/document/DNS/khoindns.mobileconfig?sign=1\n\n https://i.diawi.com/h714XM\n\n คีย์\nDoDEE"  # Replace this with the actual game link
            await interaction.response.send_message(
                f"✅ {interaction.user.mention}, คุณสามารถโหลดตัวเกมได้ที่นี่:\n{game_link}",
                ephemeral=True
            )
        else:
            # Send a failure message if the user does not have the correct role
            await interaction.response.send_message(
                "❌ คุณไม่มีสิทธิ์ในการรับตัวเกมนี้ กรุณาติดต่อแอดมิน",
                ephemeral=True
            )

class SeasonView(View):
    def __init__(self):
        super().__init__()
        self.add_item(SeasonPriceDropdown())
        self.add_item(AdminContactButton())
        self.add_item(GetGameButton())  # Add the new button here

class DailyView(View):
    def __init__(self):
        super().__init__()
        self.add_item(DailyPriceDropdown())
        self.add_item(AdminContactButton())

@bot.event
async def on_ready():
    print(f"✅ บอท {bot.user} พร้อมทำงานแล้ว!")
    check_tiktok_live.start()  # เริ่มต้น Task ตรวจสอบการไลฟ์
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")

        # Add persistent view
        bot.add_view(PersistentView())

        # Restore views in active channels
        for guild in bot.guilds:
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel) and channel.name.startswith(("order-", "support-")):
                    view = PersistentView()
                    active_views[channel.id] = view
                    try:
                        async for message in channel.history(limit=100):
                            if message.author == bot.user and "ช่องทางติดต่อแอดมิน" in message.content:
                                await message.edit(view=view)
                                break
                    except discord.HTTPException:
                        continue

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
                          "• ROV iOS รายซีซั่น (26/04/68)   🟢\n"
                          "• ROV iOS รายวัน (26/04/68)    🟢\n"
                          "• ROV Android                 🟢\n"
                          "• Free Fire                   🟢\n"
                          "• 8 Ball Pool (เจล)            🟢\n"
                          "```")
        await status_channel.send(status_message)

    daily_channel = bot.get_channel(DAILY_CHANNEL_ID)
    if daily_channel:
        embed1 = discord.Embed(
            title="⚔️ ROV iOS PREMIUM SERVICES ⚔️",
            description=(
                "# 🌟 Premium Features\n"
                "> 💦 ต้อนรับหน้าร้อนด้วยโปรสุดพิเศษ\n"
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
        embed1.set_thumbnail(url="https://media.discordapp.net/attachments/1366823031309078558/1366823437066178703/IMG_0267.png?ex=68145345&is=681301c5&hm=116e894668c93ee880d0b513da19b49d48d5557e4c62e86facbaaecc038c6ca1&=&format=webp&quality=lossless&width=989&height=989")
        embed1.set_footer(text="✨ เลือกแพ็คเกจด้านล่างเพื่อสั่งซื้อ", icon_url="https://media.discordapp.net/attachments/1366823031309078558/1366823437066178703/IMG_0267.png?ex=68145345&is=681301c5&hm=116e894668c93ee880d0b513da19b49d48d5557e4c62e86facbaaecc038c6ca1&=&format=webp&quality=lossless&width=989&height=989")
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
        embed2.set_thumbnail(url="https://media.discordapp.net/attachments/1302103738164449413/1366824081101553806/att.dB0srZ2U4rRKqjuiovORCx47MUCLGNJW1Bx81KiLbBU.jpg?ex=681453df&is=6813025f&hm=dd30a9b27ccfda00e3a1295c33551fe2ab84f94b27d9a7f9aba69227fc5934ee&=&format=webp&width=989&height=989")
        embed2.set_footer(text="✨ เลือกแพ็คเกจด้านล่างเพื่อสั่งซื้อ", icon_url="https://media.discordapp.net/attachments/1302103738164449413/1366824081101553806/att.dB0srZ2U4rRKqjuiovORCx47MUCLGNJW1Bx81KiLbBU.jpg?ex=681453df&is=6813025f&hm=dd30a9b27ccfda00e3a1295c33551fe2ab84f94b27d9a7f9aba69227fc5934ee&=&format=webp&width=989&height=989")
        await season_channel.send(embed=embed2, view=SeasonView())

# Task ลบข้อความและโพสต์ใหม่ทุก 3 นาที
@tasks.loop(minutes=5)
async def clear_and_post():
    await clear_channels()
    await post_messages()


async def notify_new_key(type: str, duration: str, key: str):
    notification_channel = bot.get_channel(1357308234137866370)
    if notification_channel:
        embed = discord.Embed(
            title="🔑 มีการเพิ่มคีย์ใหม่!",
            description=f"ประเภท: {type}\nระยะเวลา: {duration}\nคีย์คงเหลือ: {len(daily_keys[duration] if type == 'day' else season_keys[duration])} คีย์",
            color=discord.Color.green()
        )
        await notification_channel.send(embed=embed)
# ไฟล์สำหรับเก็บข้อมูลการแจกของรางวัล
GIVEAWAY_DATA_FILE = "giveaway_data.json"

# ฟังก์ชันบันทึกข้อมูลการแจกของรางวัล
def save_giveaway_data(data):
    with open(GIVEAWAY_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)
        
# ฟังก์ชันโหลดข้อมูลการแจกของรางวัล
def load_giveaway_data():
    if os.path.exists(GIVEAWAY_DATA_FILE):
        try:
            with open(GIVEAWAY_DATA_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("⚠️ Invalid JSON in giveaway_data.json. Resetting to empty.")
            return {}
    return {}
# โหลดข้อมูลการแจกของรางวัลเมื่อเริ่มต้น
giveaway_data = load_giveaway_data()

# แก้ไขคำสั่ง giveaway
@bot.tree.command(name="giveaway", description="Start a giveaway")
@app_commands.describe(
    name="The name of the giveaway",
    duration="Duration in seconds"
)
async def giveaway(interaction: Interaction, name: str, duration: int):
    participants = []
    end_time = datetime.now(pytz.utc) + timedelta(seconds=duration)
    thai_tz = pytz.timezone("Asia/Bangkok")
    end_time_thai = end_time.astimezone(thai_tz)

    # บันทึกข้อมูล giveaway ใหม่
    new_giveaway_data = {
        "name": name,
        "end_time": end_time.isoformat(),
        "participants": participants,
        "completed": False  # เพิ่มสถานะการประกาศผล
    }
    save_giveaway_data(new_giveaway_data)

    view = GiveawayView(participants, new_giveaway_data)
    await interaction.response.send_message(
        embed=Embed(
            title=f"🎉 {name} Giveaway 🎉",
            description=(
                f"กดปุ่มเพื่อเข้าร่วม\n"
                f"สิ้นสุดเวลา: {end_time_thai.strftime('%H:%M:%S')} (เวลาไทย)"
            ),
            color=0x00FF00,
        ),
        view=view
    )
class JoinButton(Button):
    def __init__(self, participants, giveaway_data):
        super().__init__(label="🎉 เข้าร่วมกิจกรรม", style=ButtonStyle.success, custom_id="join_giveaway")
        self.participants = participants
        self.giveaway_data = giveaway_data

    async def callback(self, interaction: Interaction):
        try:
            # ตรวจสอบว่า giveaway จบแล้วหรือยัง
            if self.giveaway_data.get("completed", False):
                await interaction.response.send_message(
                    "❌ กิจกรรมนี้จบไปแล้ว!",
                    ephemeral=True
                )
                return

            # ตรวจสอบว่าผู้ใช้เข้าร่วมแล้วหรือยัง
            if interaction.user.id not in self.participants:
                self.participants.append(interaction.user.id)
                self.giveaway_data["participants"] = self.participants
                save_giveaway_data(self.giveaway_data)
                
                try:
                    await interaction.response.send_message(
                        "✅ คุณได้เข้าร่วมกิจกรรมเรียบร้อยแล้ว!",
                        ephemeral=True
                    )
                except discord.errors.InteractionResponded:
                    await interaction.followup.send(
                        "✅ คุณได้เข้าร่วมกิจกรรมเรียบร้อยแล้ว!",
                        ephemeral=True
                    )
            else:
                try:
                    await interaction.response.send_message(
                        "❌ คุณได้เข้าร่วมกิจกรรมไปแล้ว!",
                        ephemeral=True
                    )
                except discord.errors.InteractionResponded:
                    await interaction.followup.send(
                        "❌ คุณได้เข้าร่วมกิจกรรมไปแล้ว!",
                        ephemeral=True
                    )

        except Exception as e:
            print(f"เกิดข้อผิดพลาด: {e}")
            try:
                await interaction.response.send_message(
                    "❌ เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง",
                    ephemeral=True
                )
            except:
                pass

class GiveawayView(View):
    def __init__(self, participants, giveaway_data):
        super().__init__(timeout=None)
        self.add_item(JoinButton(participants, giveaway_data))

# แก้ไขฟังก์ชันเช็คผู้ชนะ
@tasks.loop(seconds=10)
async def check_giveaway_winner():
    try:
        giveaway_data = load_giveaway_data()
        
        # เช็คว่ามีข้อมูล giveaway หรือไม่
        if not giveaway_data or "end_time" not in giveaway_data:
            return

        # เช็คว่าประกาศผลไปแล้วหรือยัง
        if giveaway_data.get("completed", False):
            return

        end_time = datetime.fromisoformat(giveaway_data["end_time"])
        current_time = datetime.now(pytz.utc)
            
        if current_time >= end_time:
            channel = bot.get_channel(1364857076911833159)
            if not channel:
                print("❌ ไม่พบช่องสำหรับประกาศผล")
                return

            participants = giveaway_data.get("participants", [])
                
            if participants:
                # สุ่มผู้ชนะเพียง 1 คน
                winner_id = random.choice(participants)
                await channel.send(
                    f"🎉 **ผลการแจกของรางวัล!**\n"
                    f"🎁 รางวัล: **{giveaway_data['name']}**\n"
                    f"👑 ผู้ชนะคือ: <@{winner_id}>\n"
                    f"🌟 ยินดีด้วย!"
                )
            else:
                await channel.send(
                    f"❌ **{giveaway_data['name']}**\n"
                    "😢 ไม่มีผู้เข้าร่วมกิจกรรม"
                )

            # เคลียร์ข้อมูลหลังประกาศผล
            giveaway_data = {
                "name": "",
                "end_time": "",
                "participants": [],
                "completed": True
            }
            save_giveaway_data(giveaway_data)
                    
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการตรวจสอบผู้ชนะ: {e}")

@bot.event
async def on_ready():
    print(f"✅ บอท {bot.user} พร้อมทำงานแล้ว!")
    bot.add_view(GiveawayView([], giveaway_data))  # Provide empty participants and giveaway_data
    check_giveaway_winner.start()
    clear_and_post.start()
    reset_daily_sales.start()
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
        save_daily_keys()
        await notify_new_key("day", duration, key)
        await interaction.response.send_message(f"✅ เพิ่มคีย์สำหรับ {duration} เรียบร้อยแล้ว", ephemeral=True)
    elif type == "season" and duration in season_keys:
        season_keys[duration].append(key)
        save_keys()
        await notify_new_key("season", duration, key)
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

    if type == "day" and duration in daily_keys:
        if key in daily_keys[duration]:
            daily_keys[duration].remove(key)
            save_daily_keys()
            await interaction.response.send_message(f"✅ ลบคีย์ {key} สำหรับ {duration} เรียบร้อยแล้ว", ephemeral=True)
        else:
            await interaction.response.send_message("❌ ไม่พบคีย์ที่ระบุ", ephemeral=True)
    elif type == "season" and duration in season_keys:
        if key in season_keys[duration]:
            season_keys[duration].remove(key)
            save_keys()
            await interaction.response.send_message(f"✅ ลบคีย์ {key} สำหรับ {duration} เรียบร้อยแล้ว", ephemeral=True)
        else:
            await interaction.response.send_message("❌ ไม่พบคีย์ที่ระบุ", ephemeral=True)
    else:
        await interaction.response.send_message("❌ ไม่พบระยะเวลาที่ระบุ", ephemeral=True)

@bot.tree.command(name="list", description="เช็คคีย์ทั้งหมด (Admin only)")
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

@bot.tree.command(name="shop", description="ดูข้อมูลร้าน")
async def shop_status(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏪 ข้อมูลร้าน",
        description="ร้านขายโปร ROV iOS ",
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name="📊 สถิติร้าน",
        value=f"👥 ลูกค้าทั้งหมด: {len(interaction.guild.members)}\n"
              f"💰 ยอดขายวันนี้: {daily_sales} บาท\n"
              f"⭐ คะแนนรีวิว: 4.9/5.0",
        inline=False
    )
    
    embed.add_field(
        name="⏰ เวลาทำการ",
        value="เปิดทุกวัน 24 ชม.",
        inline=True
    )
    
    embed.set_thumbnail(url="https://media.discordapp.net/attachments/1366123564771835994/1367160525493899345/att.-tSGKz9H0h_YYa1oXLy-3Y08qniWWH4WoIuvlicUENA.jpg?ex=68143bb5&is=6812ea35&hm=7993be233d805b54f1b6cc3535b6a41fee01e69457ac43178dd33fbf180f05ef&=&format=webp&width=989&height=989")
    embed.set_footer(text="อัพเดทล่าสุด")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="review", description="รีวิวสินค้า")
@app_commands.describe(rating="คะแนน 1-5 ดาว", comment="ความคิดเห็นเพิ่มเติม")
async def review(interaction: discord.Interaction, rating: int, comment: str = None):
    if rating < 1 or rating > 5:
        await interaction.response.send_message("❌ กรุณาให้คะแนน 1-5 ดาว", ephemeral=True)
        return
        
    stars = "⭐" * rating
    embed = discord.Embed(
        title="📝 รีวิวจากลูกค้า",
        description=f"{stars}\n\n{comment if comment else 'ไม่มีความคิดเห็นเพิ่มเติม'}",
        color=discord.Color.green()
    )
    embed.set_author(
        name=interaction.user.name,
        icon_url=interaction.user.avatar.url
    )
    
    review_channel = bot.get_channel(1337638812293267546)
    await review_channel.send(embed=embed)
    await interaction.response.send_message("✅ ขอบคุณสำหรับรีวิว!", ephemeral=True)

@bot.tree.command(name="sync", description="Sync slash commands (Admin only)")
async def sync(interaction: discord.Interaction):
    if not any(role.name == "Admin" for role in interaction.user.roles):
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้", ephemeral=True)
        return
        
    try:
        print("🔄 กำลัง Sync commands...")
        synced = await bot.tree.sync()
        print(f"✅ Sync สำเร็จ! ({len(synced)} คำสั่ง)")
        await interaction.response.send_message(
            f"✅ Sync commands สำเร็จ! ({len(synced)} คำสั่ง)",
            ephemeral=True
        )
    except Exception as e:
        print(f"❌ Sync ไม่สำเร็จ: {e}")
        await interaction.response.send_message(
            f"❌ Sync ไม่สำเร็จ: {e}",
            ephemeral=True
        )


@bot.event
async def on_message(message):
    if message.channel.id == 1367747079253786715:
        if message.content == ".":
            try:
                embed = discord.Embed(
                    title="🎮 ดาวน์โหลดเกม ROV iOS",
                    description=(
                        "# 📱 ข้อมูลเกม\n"
                        "> 🎯 อัพเดทใหม่ล่าสุด!\n"
                        "> 🛡️ ระบบป้องกันการแบนขั้นสูง\n"
                        "> ⚡ เล่นได้ทุกโหมด\n\n"
                        "# 🔑 คีย์ใช้งาน\n"
                        "```\n DoDEE \n```\n\n"
                        "# ⚠️ คำแนะนำ\n"
                        "> 📌 ติดตั้ง DNS ก่อนดาวน์โหลดเกม\n"
                        "> 🔰 รับประกันความปลอดภัย 100%\n"
                        "> 📱 รองรับ iOS 15 ขึ้นไป\n"
                        "> ⚡ อัพเดทล่าสุด: 03/05/2568"
                    ),
                    color=0x2ecc71
                )
                
                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1301468241335681024/1368106455525363743/IMG_8041.jpg?ex=681703ed&is=6815b26d&hm=bf9d25bac35d73a95e375356601d04770ffd0f95835b70d51cd025ae19bc429a&format=webp&width=814&height=814")
                
                class DownloadView(discord.ui.View):
                    def __init__(self):
                        super().__init__()
                        
                        # ปุ่มดาวน์โหลดเกมลิงก์ที่ 1
                        game_button1 = discord.ui.Button(
                            label="📱 ดาวน์โหลดเกม (ลิงก์ 1)",
                            url="https://i.diawi.com/h714XM",
                            style=discord.ButtonStyle.url
                        )
                        self.add_item(game_button1)
                        
                        # ปุ่มดาวน์โหลดเกมลิงก์ที่ 2
                        game_button2 = discord.ui.Button(
                            label="📱 ดาวน์โหลดเกม (ลิงก์ 2)", 
                            url="https://kravasigner.com/install?uuid=a2db40b4-dad7-4e57-9eab-253d44c807e2",
                            style=discord.ButtonStyle.url
                        )
                        self.add_item(game_button2)

                        #ปุ่มดาวน์โหลดเกมลิงค์ที่ 3
                        game_button3 = discord.ui.Button(
                            label="📱 ดาวน์โหลดเกม (Esign,Gbox)",
                            url="https://drive.google.com/file/d/1zme240GygwAsS1NDLSJNxbvpm3LX2m0a/view?usp=drivesdk",
                            style=discord.ButtonStyle.url
                        )
                        self.add_item(game_button3)
                        
                        # ปุ่มดาวน์โหลด DNS
                        dns_button = discord.ui.Button(
                            label="🛡️ ติดตั้ง DNS",
                            url="https://khoindvn.io.vn/document/DNS/khoindns.mobileconfig?sign=1",
                            style=discord.ButtonStyle.url
                        )
                        self.add_item(dns_button)

                        #ไฟล์ทรัพยากร
                        extra_button = discord.ui.Button(
                            label="🪄 ไฟล์ Extra",
                            url="https://drive.google.com/file/d/1hBVggnrFQJ4gWyVxKhr0ZI8xy2Xn-4xK/view?usp=drivesdk",
                            style=discord.ButtonStyle.url
                        )
                        self.add_item(extra_button)

                        #วิดิโอสอนโหลด
                        video_howtoload = discord.ui.Button(
                            label="⚒️ วิดิโอสอนโหลด",
                            url="https://youtube.com/shorts/NoHAxik3Ilo?si=A_5FPbUJHc8wwzbt",
                            style=discord.ButtonStyle.url
                        )
                        self.add_item(video_howtoload)
                                                # ปุ่มวิธีติดตั้ง
                        @discord.ui.button(label="📖 วิธีติดตั้ง", style=discord.ButtonStyle.primary)
                        async def guide(self, interaction: discord.Interaction, button: discord.ui.Button):
                            await interaction.response.send_message(
                                "📝 **วิธีการติดตั้ง**\n\n"
                                "**ขั้นตอนที่ 1: ติดตั้ง DNS**\n"
                                "1. เปิดลิงก์ DNS\n"
                                "2. กดติดตั้ง Profile\n"
                                "3. ตั้งค่า > ทั่วไป > VPN & DNS\n"
                                "4. เปิดใช้งาน DNS\n\n"
                                "**ขั้นตอนที่ 2: ติดตั้งเกม**\n"
                                "1. เปิดลิงก์ดาวน์โหลด\n" 
                                "2. กด Install/ติดตั้ง\n"
                                "3. รอจนติดตั้งเสร็จ\n\n"
                                "**ขั้นตอนที่ 3: เริ่มใช้งาน**\n"
                                "1. เปิดเกมที่ติดตั้ง\n"
                                "2. ใส่คีย์ RoV / V2.0\n"
                                "3. เริ่มเล่นได้เลย!",
                                ephemeral=True
                            )

                await message.reply(embed=embed, view=DownloadView())
                
            except discord.HTTPException as e:
                print(f"❌ ไม่สามารถส่งข้อความได้: {e}")
    await bot.process_commands(message)
if __name__ == "__main__":
    from myserver import run_server
    import threading
    server_thread = threading.Thread(target=run_server)
    server_thread.start()
    bot.run(TOKEN)
