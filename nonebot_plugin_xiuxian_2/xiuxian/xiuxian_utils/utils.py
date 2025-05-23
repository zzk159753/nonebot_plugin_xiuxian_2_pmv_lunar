import asyncio
import datetime
import io
import json
import math
import os
import random
import re
from base64 import b64encode
from io import BytesIO
from pathlib import Path

import unicodedata
from PIL import Image, ImageDraw, ImageFont
from nonebot.adapters import MessageSegment
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent
)
from nonebot.adapters.onebot.v11 import MessageSegment
from wcwidth import wcwidth

from .clean_utils import simple_md
from .other_set import OtherSet
from .xiuxian2_handle import sql_message
from ..database_utils.move_database import read_move_data
from ..types.user_info import UserInfo
from ..xiuxian_config import XiuConfig
from ..xiuxian_data.data.灵根_data import root_data
from ..xiuxian_place import place

DATABASE = Path() / "data" / "xiuxian"
boss_img_path = Path() / "data" / "xiuxian" / "boss_img"


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(obj, bytes):
            return str(obj, encoding='utf-8')
        if isinstance(obj, int):
            return int(obj)
        elif isinstance(obj, float):
            return float(obj)
        else:
            return super(MyEncoder, self).default(obj)


async def check_user_type(user_id, need_type):
    """
    说明: 匹配用户状态，返回是否状态一致
    :param user_id: type = str 用户ID
    :param need_type: type = int 需求状态 -1为移动中  0为空闲中  1为闭关中  2为悬赏令中
    :returns: isType: 是否一致 ， msg: 消息体
    """
    isType = False
    msg = ''
    user_cd_message = await sql_message.get_user_cd(user_id)
    if user_cd_message is None:
        user_type = 0
    else:
        user_type = user_cd_message['type']
    # 此处结算移动
    if user_type == need_type:  # 状态一致
        isType = True
    else:
        type_msgs = {1: simple_md("道友现在在闭关呢，小心走火入魔！若有要事，请先", "出关", "出关", "！"),
                     2: simple_md("道友现在在做悬赏令呢！请先着手", "完成", "悬赏令结算", "当前悬赏！"),
                     3: simple_md("道友现在正在", "秘境", "秘境结算", "中，分身乏术！"),
                     4: simple_md("道友正在修炼中，请抱元守一，聚气凝神，勿要分心！\r如有要事，请先", "停止修炼", "停止修炼",
                                  "！！"),
                     5: simple_md("道友正在虚神界修炼中，请抱元守一，聚气凝神，勿要分心！若有要事，请先", "出关", "出关",
                                  "！"),
                     6: simple_md("道友正在进行", "位面挑战", "查看挑战", "中，请全力以赴！！"),
                     7: simple_md("道友正在", "炼丹", "丹炉状态", "呢，请全神贯注！！"),
                     0: "道友现在什么都没干呢~"}
        if user_type in type_msgs:
            msg = type_msgs[user_type]
        elif user_type == -1:
            # 前面添加赶路检测
            work_time = datetime.datetime.strptime(
                user_cd_message['create_time'], "%Y-%m-%d %H:%M:%S.%f"
            )
            pass_time = (datetime.datetime.now() - work_time).seconds // 60  # 时长计算
            move_info = await read_move_data(user_id)
            need_time = move_info["need_time"]
            place_name = place.get_place_name(move_info["to_id"])
            if pass_time < need_time:
                last_time = math.ceil(need_time - pass_time)
                msg = f"道友现在正在赶往【{place_name}】中！预计还有{last_time}分钟到达目的地！！"
            else:  # 移动结算逻辑
                await sql_message.do_work(user_id, 0)
                place_id = move_info["to_id"]
                await place.set_now_place_id(user_id, place_id)
                msg = f"道友成功抵达【{place_name}】！！！"
        else:
            msg = '未知状态错误！！！'

    return isType, msg


async def check_user(event: GroupMessageEvent) -> UserInfo:
    """
    判断用户信息是否存在
    :返回参数:
      * `isUser: 是否存在
      * `user_info: 用户
      * `msg: 消息体
    """
    user_id = int(event.get_user_id())
    user_info: UserInfo = await sql_message.get_user_info_with_id(user_id)
    return user_info


class Txt2Img:
    """文字转图片"""

    def __init__(self, size=32):
        self.BACKGROUND_FILE = DATABASE / "image" / "background.png"
        self.BOSS_IMG = DATABASE / "boss_img"
        self.FONT_FILE = DATABASE / "font" / "SarasaMonoSC-Bold.ttf"
        self.BANNER_FILE = DATABASE / "image" / "banner.png"
        self.font = str(self.FONT_FILE)
        self.font_size = int(size)
        self.use_font = ImageFont.truetype(font=self.font, size=self.font_size)
        self.upper_size = 30
        self.below_size = 30
        self.left_size = 40
        self.right_size = 55
        self.padding = 12
        self.img_width = 780
        self.black_clor = (255, 255, 255)
        self.line_num = 0

        self.user_font_size = int(size * 1.5)
        self.lrc_font_size = int(size)
        self.font_family = str(self.FONT_FILE)
        self.share_img_width = 1080
        self.line_space = int(size)
        self.lrc_line_space = int(size / 2)

    # 预处理
    def prepare(self, text, scale):
        text = unicodedata.normalize("NFKC", text)
        if scale:
            max_text_len = self.img_width - self.left_size - self.right_size
        else:
            max_text_len = 1080 - self.left_size - self.right_size
        use_font = self.use_font
        line_num = self.line_num
        text_len = 0
        text_new = ""
        for x in text:
            text_new += x
            text_len += use_font.getlength(x)
            if x == "\r":
                text_len = 0
            if text_len >= max_text_len:
                text_len = 0
                text_new += "\r"
        text_new = text_new.replace("\r\r", "\r")
        text_new = text_new.rstrip()
        line_num = line_num + text_new.count("\r")
        return text_new, line_num

    def sync_draw_to(self, text, boss_name="", scale=True):
        font_size = self.font_size
        black_clor = self.black_clor
        upper_size = self.upper_size
        below_size = self.below_size
        left_size = self.left_size
        padding = self.padding
        img_width = self.img_width
        use_font = self.use_font
        text, line_num = self.prepare(text=text, scale=scale)
        if scale:
            if line_num < 5:
                blank_space = int(5 - line_num)
                line_num = 5
                text += "\r"
                for k in range(blank_space):
                    text += "(^ ᵕ ^)\r"
            else:
                line_num = line_num
        else:
            img_width = 1080
            line_num = line_num
        img_hight = int(upper_size + below_size + font_size * (line_num + 1) + padding * line_num)
        out_img = Image.new(mode="RGB", size=(img_width, img_hight),
                            color=black_clor)
        draw = ImageDraw.Draw(out_img, "RGBA")

        # 设置
        banner_size = 12
        border_color = (220, 211, 196)
        out_padding = 15
        mi_img = Image.open(self.BACKGROUND_FILE)
        mi_banner = Image.open(self.BANNER_FILE).resize(
            (banner_size, banner_size), resample=3
        )

        # 添加背景
        for x in range(int(math.ceil(img_hight / 100))):
            out_img.paste(mi_img, (0, x * 100))

        # 添加边框
        def draw_rectangle(draw, rect, width):
            for i in range(width):
                draw.rectangle(
                    (rect[0] + i, rect[1] + i, rect[2] - i, rect[3] - i),
                    outline=border_color,
                )

        draw_rectangle(
            draw, (out_padding, out_padding, img_width - out_padding, img_hight - out_padding), 2
        )

        # 添加banner
        out_img.paste(mi_banner, (out_padding, out_padding))
        out_img.paste(
            mi_banner.transpose(Image.FLIP_TOP_BOTTOM),
            (out_padding, img_hight - out_padding - banner_size + 1),
        )
        out_img.paste(
            mi_banner.transpose(Image.FLIP_LEFT_RIGHT),
            (img_width - out_padding - banner_size + 1, out_padding),
        )
        out_img.paste(
            mi_banner.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM),
            (img_width - out_padding - banner_size + 1, img_hight - out_padding - banner_size + 1),
        )

        # 绘制文字
        draw.text(
            (left_size, upper_size),
            text,
            font=use_font,
            fill=(125, 101, 89),
            spacing=padding,
        )
        # 贴boss图
        if boss_name:
            boss_img_path = self.BOSS_IMG / f"{boss_name}.png"
            if os.path.exists(boss_img_path):
                boss_img = Image.open(boss_img_path)
                base_cc = boss_img.height / img_hight
                boss_img_w = int(boss_img.width / base_cc)
                boss_img_h = int(boss_img.height / base_cc)
                boss_img = boss_img.resize((int(boss_img_w), int(boss_img_h)), Image.Resampling.LANCZOS)
                out_img.paste(
                    boss_img,
                    (int(img_width - boss_img_w), int(img_hight - boss_img_h)),
                    boss_img
                )
        if XiuConfig().img_send_type == "io":
            return out_img
        elif XiuConfig().img_send_type == "base64":
            return self.img2b64(out_img)

    def img2b64(self, out_img) -> str:
        """ 将图片转换为base64 """
        buf = BytesIO()
        out_img.save(buf, format="PNG")
        base64_str = "base64://" + b64encode(buf.getvalue()).decode()
        return base64_str

    async def io_draw_to(self, text, boss_name="", scale=True):  # draw_to
        loop = asyncio.get_running_loop()
        out_img = await loop.run_in_executor(None, self.sync_draw_to, text, boss_name, scale)
        return await loop.run_in_executor(None, self.save_image_with_compression, out_img)

    async def save(self, title, lrc):
        """保存图片,涉及title时使用"""
        border_color = (220, 211, 196)
        text_color = (125, 101, 89)

        out_padding = 30
        padding = 45
        banner_size = 20

        user_font = ImageFont.truetype(self.font_family, self.user_font_size)
        lyric_font = ImageFont.truetype(self.font_family, self.lrc_font_size)

        if title == ' ':
            title = ''

        lrc = self.wrap(lrc)

        if lrc.find("\r") > -1:
            lrc_rows = len(lrc.split("\r"))
        else:
            lrc_rows = 1

        w = self.share_img_width

        if title:
            inner_h = (
                    padding * 2
                    + self.user_font_size
                    + self.line_space
                    + self.lrc_font_size * lrc_rows
                    + (lrc_rows - 1) * self.lrc_line_space
            )
        else:
            inner_h = (
                    padding * 2
                    + self.lrc_font_size * lrc_rows
                    + (lrc_rows - 1) * self.lrc_line_space
            )

        h = out_padding * 2 + inner_h

        out_img = Image.new(mode="RGB", size=(w, h), color=(255, 255, 255))
        draw = ImageDraw.Draw(out_img)

        mi_img = Image.open(self.BACKGROUND_FILE)
        mi_banner = Image.open(self.BANNER_FILE).resize(
            (banner_size, banner_size), resample=3
        )

        # add background
        for x in range(int(math.ceil(h / 100))):
            out_img.paste(mi_img, (0, x * 100))

        # add border
        def draw_rectangle(draw, rect, width):
            for i in range(width):
                draw.rectangle(
                    (rect[0] + i, rect[1] + i, rect[2] - i, rect[3] - i),
                    outline=border_color,
                )

        draw_rectangle(
            draw, (out_padding, out_padding, w - out_padding, h - out_padding), 2
        )

        # add banner
        out_img.paste(mi_banner, (out_padding, out_padding))
        out_img.paste(
            mi_banner.transpose(Image.FLIP_TOP_BOTTOM),
            (out_padding, h - out_padding - banner_size + 1),
        )
        out_img.paste(
            mi_banner.transpose(Image.FLIP_LEFT_RIGHT),
            (w - out_padding - banner_size + 1, out_padding),
        )
        out_img.paste(
            mi_banner.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM),
            (w - out_padding - banner_size + 1, h - out_padding - banner_size + 1),
        )

        if title:
            tmp_img = Image.new("RGB", (1, 1))
            tmp_draw = ImageDraw.Draw(tmp_img)
            user_bbox = tmp_draw.textbbox((0, 0), title, font=user_font, spacing=self.line_space)
            # 四元组(left, top, right, bottom)
            user_w = user_bbox[2] - user_bbox[0]  # 宽度 = right - left
            user_h = user_bbox[3] - user_bbox[1]
            draw.text(
                ((w - user_w) // 2, out_padding + padding),
                title,
                font=user_font,
                fill=text_color,
                spacing=self.line_space,
            )
            draw.text(
                (
                    out_padding + padding,
                    out_padding + padding + self.user_font_size + self.line_space,
                ),
                lrc,
                font=lyric_font,
                fill=text_color,
                spacing=self.lrc_line_space,
            )
        else:
            draw.text(
                (out_padding + padding, out_padding + padding),
                lrc,
                font=lyric_font,
                fill=text_color,
                spacing=self.lrc_line_space,
            )
        if XiuConfig().img_send_type == "io":
            buf = BytesIO()
            if XiuConfig().img_type == "webp":
                out_img.save(buf, format="WebP")
            elif XiuConfig().img_type == "jpeg":
                out_img.save(buf, format="JPEG")
            buf.seek(0)
            return buf
        elif XiuConfig().img_send_type == "base64":
            return self.img2b64(out_img)

    def save_image_with_compression(self, out_img):
        """对传入图片进行压缩"""
        img_byte_arr = io.BytesIO()
        compression_quality = 100 - XiuConfig().img_compression_limit  # 质量从100到0
        if not (0 <= XiuConfig().img_compression_limit <= 100):
            compression_quality = 0

        if XiuConfig().img_type == "webp":
            out_img.save(img_byte_arr, format="WebP", quality=compression_quality)
        elif XiuConfig().img_type == "jpeg":
            out_img.save(img_byte_arr, format="JPEG", quality=compression_quality)
        else:
            out_img.save(img_byte_arr, format="WebP", quality=compression_quality)
        img_byte_arr.seek(0)
        return img_byte_arr

    def wrap(self, string):
        max_width = int(1850 / self.lrc_font_size)
        temp_len = 0
        result = ''
        for ch in string:
            result += ch
            temp_len += wcwidth(ch)
            if ch == '\r':
                temp_len = 0
            if temp_len >= max_width:
                temp_len = 0
                result += '\r'
        result = result.rstrip()
        return result


async def get_msg_pic(msg, boss_name="", scale=True):
    img = Txt2Img()
    if XiuConfig().img_send_type == "io":
        pic = await img.io_draw_to(msg, boss_name, scale)
    elif XiuConfig().img_send_type == "base64":
        pic = img.sync_draw_to(msg, boss_name, scale)
    return pic


async def send_msg_handler(bot, event, *args):
    """
    统一消息发送处理器
    :param bot: 机器人实例
    :param event: 事件对象
    :param args: 消息内容列表
    """

    if XiuConfig().merge_forward_send == 1:
        if len(args) == 3:
            name, uin, msgs = args
            messages = [{"type": "node", "data": {"name": name, "uin": uin, "content": msg}} for msg in msgs]
            if isinstance(event, GroupMessageEvent):
                await bot.call_api("send_group_forward_msg", group_id=event.group_id, messages=messages)
            else:
                await bot.call_api("send_private_forward_msg", user_id=event.user_id, messages=messages)
        elif len(args) == 1 and isinstance(args[0], list):
            messages = args[0]
            if isinstance(event, GroupMessageEvent):
                await bot.call_api("send_group_forward_msg", group_id=event.group_id, messages=messages)
            else:
                await bot.call_api("send_private_forward_msg", user_id=event.user_id, messages=messages)
        else:
            raise ValueError("参数数量或类型不匹配")
    elif XiuConfig().merge_forward_send == 2:  # 合并作为文本发送
        if len(args) == 3:
            name, uin, msgs = args
            messages = '\r'.join(msgs)

            if isinstance(event, GroupMessageEvent):
                await bot.send(event=event, message=messages)
            else:
                await bot.send_private_msg(user_id=event.user_id, message=messages)
        elif len(args) == 1 and isinstance(args[0], list):
            messages = args[0]
            try:
                messages = '\r'.join([str(msg['data']['content']) for msg in messages])
            except TypeError:
                messages = '\r'.join([str(msg) for msg in messages])
            if isinstance(event, GroupMessageEvent):
                await bot.send(event=event, message=messages)
            else:
                await bot.send_private_msg(user_id=event.user_id, message=messages)
        else:
            raise ValueError("参数数量或类型不匹配")
    else:
        if len(args) == 3:
            name, uin, msgs = args
            img = Txt2Img()
            messages = '\r'.join(msgs)
            if XiuConfig().img_send_type == "io":
                img_data = await img.io_draw_to(messages)
            elif XiuConfig().img_send_type == "base64":
                img_data = img.sync_draw_to(messages)
            if isinstance(event, GroupMessageEvent):
                await bot.send(event=event, message=MessageSegment.image(img_data))
            else:
                await bot.send_private_msg(user_id=event.user_id, message=MessageSegment.image(img_data))

        elif len(args) == 1 and isinstance(args[0], list):
            messages = args[0]
            img = Txt2Img()
            messages = '\r'.join([str(msg['data']['content']) for msg in messages])
            if XiuConfig().img_send_type == "io":
                img_data = await img.io_draw_to(messages)
            elif XiuConfig().img_send_type == "base64":
                img_data = img.sync_draw_to(messages)
            if isinstance(event, GroupMessageEvent):
                await bot.send(event=event, message=MessageSegment.image(img_data))
            else:
                await bot.send_private_msg(user_id=event.user_id, message=MessageSegment.image(img_data))
        else:
            raise ValueError("参数数量或类型不匹配")


def number_to(num):
    """
    递归实现，精确为最大单位值 + 小数点后一位
    处理科学计数法表示的数值
    """

    # 处理列表类数据
    if num:
        pass
    else:
        # 打回
        return "零"
    if isinstance(num, str):
        hf = ""
        num = num.split("、")
        final_num = ""
        for num_per in num:
            # 对列表型数值每个处理输出到新list
            # 处理字符串输入
            if not isinstance(num_per, int):
                # 处理坑爹的伤害列表
                if num_per[-2:] == "伤害":
                    num_per = num_per[:-2]
                    hf = "点伤害"
                num_per = int(num_per)
            # 处理负数输出
            fh = ""
            if num_per < 0:
                fh = "-"
                num_per = abs(num_per)

            def strofsize(num_per, level):
                if level >= 29:
                    return num_per, level
                elif num_per >= 10000:
                    num_per /= 10000
                    level += 1
                    return strofsize(num_per, level)
                else:
                    return num_per, level

            units = ['', '万', '亿', '万亿', '兆', '万兆', '亿兆', '万亿兆', '京', '万京', '亿京', '万亿京', '兆京',
                     '万兆京', '亿兆京', '万亿兆京', '垓', '万垓', '亿垓', '万亿垓',
                     '兆垓', '万兆垓', '亿兆垓', '万亿兆垓', '京垓', '万京垓',
                     '亿京垓', '万亿京垓', '兆京垓', '万兆京垓']
            # 处理科学计数法
            if "e" in str(num_per):
                num_per = float(f"{num_per:.1f}")
            num_per, level = strofsize(num_per, 0)
            if level >= len(units):
                level = len(units) - 1
            final_num += "、" + f"{fh}{round(num_per, 1)}{units[level]}" + hf
        return final_num[1:]
    else:
        # 处理字符串输入
        if isinstance(num, str):
            # 处理坑爹的伤害列表
            if num[-2:] == "伤害":
                num = num[:-2]
            num = int(num)
        # 处理负数输出
        fh = ""
        if num < 0:
            fh = "-"
            num = abs(num)

        def strofsize(num, level):
            if level >= 29:
                return num, level
            elif num >= 10000:
                num /= 10000
                level += 1
                return strofsize(num, level)
            else:
                return num, level

        units = ['', '万', '亿', '万亿', '兆', '万兆', '亿兆', '万亿兆', '京', '万京', '亿京', '万亿京', '兆京',
                 '万兆京', '亿兆京', '万亿兆京', '垓', '万垓', '亿垓', '万亿垓',
                 '兆垓', '万兆垓', '亿兆垓', '万亿兆垓', '京垓', '万京垓',
                 '亿京垓', '万亿京垓', '兆京垓', '万兆京垓']
        # 处理科学计数法
        if "e" in str(num):
            num = float(f"{num:.1f}")
        num, level = strofsize(num, 0)
        if level >= len(units):
            level = len(units) - 1
        final_num = f"{fh}{round(num, 1)}{units[level]}"
    return final_num


async def get_id_from_str(msg: str | list, no: int = 1):
    """
    将消息中的首个字符组合转换为用户id
    :param msg: 从args中获取的消息字符串
    :param no: 获取第几个字符串集合为用户名称
    :return: 如果有该用户，返回用户ID，若无，返回None
    """
    if isinstance(msg, str):
        user_name = re.findall(r"[\u4e00-\u9fa5_a-zA-Z]+", msg)
    else:
        user_name = msg
    if not user_name:
        return None
    print(user_name[no - 1])
    user_id = await sql_message.get_user_id(user_name[no - 1]) if len(user_name) >= no else None
    user_id = int(user_id) if user_id else None
    return user_id


async def pic_msg_format(msg, event):
    user_name = (
        event.sender.card if event.sender.card else event.sender.nickname
    )
    result = "@" + user_name + "\r" + msg
    return result


def linggen_get():
    """获取灵根信息"""
    data = root_data
    rate_dict = {}
    for i, v in data.items():
        rate_dict[i] = v["type_rate"]
    lgen = OtherSet().calculated(rate_dict)
    if data[lgen]["type_flag"]:
        flag = random.choice(data[lgen]["type_flag"])
        root = random.sample(data[lgen]["type_list"], flag)
        msg = ""
        for j in root:
            if j == root[-1]:
                msg += j
                break
            msg += (j + "、")

        return msg + '属性灵根', lgen
    else:
        root = random.choice(data[lgen]["type_list"])
        return root, lgen
