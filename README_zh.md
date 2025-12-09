# BLUETTI 集成用于 Home Assistant

[🇬🇧 英文](./README.md) | [🇳🇱 荷兰语](./README_nl.md) | [🇩🇪 德语](./README_de.md)
| [🇨🇳 简体中文](./README_zh.md)

**BLUETTI 集成**是 Home Assistant 的内置组件，并且由 **BLUETTI**
官方支持。它允许你直接通过 Home Assistant 管理 BLUETTI 智能电站。

## ✨ 功能

- ✅ 逆变器状态
- ✅ 电池电量 (SoC)
- ✅ AC 开关
- ✅ DC 开关
- ✅ 主开关
- ✅ AC ECO 模式
- ✅ 工作模式选择器：备用、自发电、峰谷
- ✅ 灾害警报

## 🎮 支持的电站型号

> [!NOTE]
>
> 未来版本中，BLUETTI 集成将扩展以支持更多新旧电站型号。

| 电站型号   | 逆变器状态 | 电池电量 SoC | AC 开关 | DC 开关 | 主开关 | AC ECO | 模式选择器 | 灾害警报 |
| :--------- | :--------: | :----------: | :-----: | :-----: | :----: | -----: | :--------: | :------: |
| APEX300    |     ✅     |      ✅      |   ✅    |         |   ✅   |     ✅ |     ✅     |          |
| Elite100V2 |     ✅     |      ✅      |   ✅    |   ✅    |        |     ✅ |     ✅     |          |
| Elite30V2  |     ✅     |      ✅      |   ✅    |   ✅    |        |     ✅ |     ✅     |          |
| EP13K      |     ✅     |      ✅      |         |         |   ✅   |        |     ✅     |    ✅    |
| EP2000     |     ✅     |      ✅      |         |         |   ✅   |        |     ✅     |    ✅    |
| EP6K       |     ✅     |      ✅      |         |         |   ✅   |        |     ✅     |    ✅    |
| FP         |     ✅     |      ✅      |   ✅    |         |   ✅   |     ✅ |     ✅     |    ✅    |

## 📦 安装 BLUETTI 集成

### Home Assistant 操作系统

按照以下步骤在 **Home Assistant** 中安装 **BLUETTI 集成**。

你可以使用 **Advanced SSH & Web Terminal** 插件，或者通过 **SSH** 连接到你的
**Home Assistant 服务器**。

```bash
ssh username@host-ip
```

如果你在 **Windows**、**macOS** 或 **Linux** 上以 Docker 容器运行 Home
Assistant，请先登录到运行 Docker 的主机：

```bash
ssh username@host-ip
```

然后在 Home Assistant 容器中打开 shell：

```bash
docker exec -it container-name /bin/bash
```

### 安装步骤

1. **进入 Home Assistant 配置目录：**

   ```bash
   cd config 2> /dev/null || echo "你已经在 'config' 目录。继续执行步骤 2。"
   ```

2. **创建 `custom_components` 文件夹**（如果不存在）：

   ```bash
   mkdir -pv custom_components
   ```

3. **克隆 BLUETTI 集成 GitHub 仓库：**

   ```bash
   git clone https://github.com/bluetti-official/bluetti-home-assistant.git
   mv /config/bluetti-home-assistant/custom_components/bluetti /config/custom_components/bluetti
   rm -r /config/bluetti-home-assistant
   ```

4. **重启 Home Assistant** 加载新集成：
   - 对于 **Home Assistant 操作系统**：

     ```bash
     ha core restart
     ```

   - 对于 **Docker 安装**：

     ```bash
     docker restart container-name
     ```

### 通过 Home Assistant 社区商店 (HACS) 安装

**BLUETTI 集成**尚未在官方 [HACS 仓库](https://github.com/hacs/integration)
上架，需要手动添加为 **自定义仓库**。

> [!NOTE]
>
> **HACS 是什么？** HACS (_Home Assistant Community Store_) 是 Home
> Assistant 的扩展，相当于第三方集成的应用商店。在添加自定义仓库前，请确保已安装 HACS。

#### 安装步骤

1. 打开 **HACS → 集成 → 自定义仓库**（页面右上角）。

2. 添加以下仓库并选择正确类型：
   - **仓库地址:** [https://github.com/bluetti-official/bluetti-home-assistant.git](https://github.com/bluetti-official/bluetti-home-assistant.git)
   - **类型:** Integration

3. 前往 **HACS → 集成**，列表中将显示 **BLUETTI** 集成，点击安装。

4. **重启 Home Assistant** 完成安装。

## ⚙️ 集成配置

1. 前往 **设置 → 设备与服务** 打开集成列表。
   <img src="./doc/images/1-setting_devices_and_services.png" width="880">

2. 点击 **添加集成**，搜索 **bluetti**，选择 **BLUETTI 集成** 开始 OAuth 授权。
   <img src="./doc/images/2-search_and_add_integration.png" width="880">

3. 授权 **Home Assistant** 访问你的 BLUETTI 账户并连接 BLUETTI 云服务。
   <img src="./doc/images/3-oauth_agree_to_connect_with_bluetti.png">

4. 输入 BLUETTI 账户凭证登录并授权。
   <img src="./doc/images/4-oauth_enter_bluetti_account.png">

5. 确认 **Home Assistant** 可以绑定你的 BLUETTI 账户。
   <img src="./doc/images/5-oauth_link_account_to_ha.png">

6. 选择你希望在 Home Assistant 中使用和管理的 BLUETTI 设备。
   <img src="./doc/images/6-choose_bluetti_devices.png" width="880">
   <img src="./doc/images/7-bluetti_device_in_ha.png" width="880">

## ❓ 常见问题 (FAQ)

### **问题:** 安装后找不到 BLUETTI 集成？

**回答:** 检查 `custom_components` 文件夹是否在正确位置，并重启 Home Assistant。

### **问题:** 集成一直离线或无法连接 BLUETTI 服务器？

**回答:** 检查 **网络连接**、**端口设置** 和 **防火墙**，确保 **Home Assistant**
可以访问 BLUETTI 电站。

### **问题:** BLUETTI 集成可以本地工作吗？

**回答:** 暂时不能。当前集成通过云端工作，本地模式正在开发中，但需要一段时间完成。

## 🔄 更新 BLUETTI 集成

### Home Assistant 操作系统

1. **更新 BLUETTI 集成**（如有需要）：

   ```bash
   cd /config/custom_components/bluetti-home-assistant
   git pull
   ```

2. **重启 Home Assistant** 加载更新：
   - 对于 **Home Assistant 操作系统**：

     ```bash
     ha core restart
     ```

   - 对于 **Docker 安装**：

     ```bash
     docker restart container-name
     ```

### Home Assistant 社区商店

通过 HACS 管理页面更新集成。

## 📮 支持与反馈

💬 有问题、建议或反馈？请通过 **GitHub Issues** 联系我们：
[https://github.com/bluetti-official/bluetti-home-assistant/issues](https://github.com/bluetti-official/bluetti-home-assistant/issues)
