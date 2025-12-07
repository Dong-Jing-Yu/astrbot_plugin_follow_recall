from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
from astrbot.api.event import filter
from astrbot.core.message.message_event_result import MessageChain
from astrbot.api.star import Context, Star, register
from astrbot.api import AstrBotConfig, logger

@register(
    "astrbot_plugin_follow_recall",
    "东经雨",
    "在触发机器人回复的消息撤回后,机器人会同步撤回机器人回复消息",
    "0.0.1"
)
class FollowRecallPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.switch = self.config.get("Switch", True)

        # user_msg_id -> bot_msg_id
        self.follow_map = {}

    # =====================================================
    # ① 监听并记录：触发消息ID → 机器人回复ID
    # =====================================================
    @filter.on_decorating_result()
    async def record_reply(self, event: AiocqhttpMessageEvent):
        raw = event.message_obj.raw_message
        if not isinstance(raw, dict):
            return

        user_msg_id = raw.get("message_id")
        if not user_msg_id:
            return

        chain = event.get_result().chain
        if not chain:
            return

        obmsg = await event._parse_onebot_json(MessageChain(chain=chain))
        client = event.bot

        # 发送机器人回复
        if gid := event.get_group_id():
            send_result = await client.send_group_msg(group_id=int(gid), message=obmsg)
        elif uid := event.get_sender_id():
            send_result = await client.send_private_msg(user_id=int(uid), message=obmsg)
        else:
            return

        # 保存映射
        if send_result and (bot_id := send_result.get("message_id")):
            self.follow_map[str(user_msg_id)] = bot_id
            logger.info(f"[跟随撤回] 记录映射 {user_msg_id} → {bot_id}")

        # 阻止重复发送
        chain.clear()
        event.stop_event()

    ### 暂无撤回事件监听接口 ###


    async def terminate(self):
        self.follow_map.clear()
        logger.info("跟随撤回插件已卸载")
