# BLUETTI储能HA集成

[English](./README.md) | [简体中文](./README_zh.md)

BLUETTI储能集成是一个由BLUETTI官方提供的Home Assistant集成插件，支持在Home Assistant系统中使用您的BLUETTI智能储能设备。

BLUETTI储能集成github仓库地址：https://github.com/bluetti-official/bluetti-home-assistant

# ✨ 功能特性

- ✅ 逆变器状态（Inverter Status）  
- ✅ 查询电量SOC（Battery state of charge）  
- ✅ 预估续航时间（Estimated battery life）
- ✅ ECO模式切换（AC ECO，DC ECO） 
- ✅ AC/DC开关（AC/DC Switch）  
- ✅ 整机电源开关（Main unit power switch）  
- ✅ 工作模式切换（Work mode switch）：自发自用，备用电源，削峰填谷 
- ✅ 灾害预警功能（Disaster Warning）  

# 🎮 机型支持清单

|        | 逆变器状态 | 查询电量SOC | 预估续航时间 | ECO模式切换 | AC/DC开关 | 整机电源开关 | 工作模式切换 | 灾害预警功能 |
|--------|--------|------------|-------------|------------|----------|-------------|-------------|------------|
| EP13K  | ✅     | ✅        | ✅          |            |          | ✅         | ✅          | ✅         |
| EP6K   | ✅     | ✅        | ✅          |            |          | ✅         | ✅          | ✅         |
| EP2000 | ✅     | ✅        | ✅          |            |          | ✅         | ✅          | ✅         |
| FP     | ✅     | ✅        | ✅          | ✅         | ✅      | ✅         | ✅          | ✅         |
 
# 📦 安装方法

## 方法A：手动安装

1. 进入Home Assistant配置目录：
```shell
$ cd /<ha workspaces>/config/custom_components
```
2. 克隆BLUETTI储能集成github仓库：
```shell
$ git clone https://github.com/bluetti-official/bluetti-home-assistant.git
```
3. 或者下载集成的zip压缩包，并解压到：
```shell
$ unzip xxx.zip -d /<ha workspaces>/core/config/custom_components/bluetti
```
4. 重启Home Assistant系统。
<hr/>

## 方法B：通过HACS安装

由于目前Bluetti home assistant集成尚未提交至 HACS 官方仓库，需要手动添加自定义仓库。 HACS 本身是一个 Home Assistant 插件（用户需要先安装 HACS），类似应用市场，通过该应用市场来安装其他三方集成。

1. 打开 HACS → 集成 → 自定义仓库（右上角）
2. 添加仓库地址：
```shell
https://github.com/bluetti-official/bluetti-home-assistant.git
```
类型选择：Integration  
3. 接着在 HACS 的“集成”页面，就能看到Bluetti的插件，点击安装。
4. 安装后，重启Home Assistant。

# ⚙️ 配置集成

## 通过界面添加集成

1. 进入`Home Assistant` → 设置 → 设备与服务。  
   <img src="./doc/images/1-setting_devices_and_services.png" width="880">
2. 点击“添加集成”按钮，然后搜索品牌关键词`bluetti`；选择`BLUETTI`集成进行下一步的OAUTH授权登录。  
   <img src="./doc/images/2-search_and_add_integration.png" width="880">
3. 您必须同意`Home Assistant`访问您的BLUETTI账号并与BLUETTI云服务建立联系。  
   <img src="./doc/images/3-oauth_agree_to_connect_with_bluetti.png">
4. 输入您的BLUETTI账号以进行授权登录。  
   <img src="./doc/images/4-oauth_enter_bluetti_account.png">
5. 您必须同意`Home Assistant`链接使用您的BLUETTI账号。  
   <img src="./doc/images/5-oauth_link_account_to_ha.png">
6. 选择需要在`Home Assistant`中使用和管理的BLUETTI电站设备。  
   <img src="./doc/images/6-choose_bluetti_devices.png" width="880">  
   <img src="./doc/images/7-bluetti_device_in_ha.png" width="880">

# ❓ 常见问题

- **没有显示BLUETTI集成？**  
  检查`custom_components`路径是否正确，并确认是否已经重启`Home Assistant`系统。

- **设备不在线、设备联网失败**  
  请检查网络、端口、防火墙，确保`Home Assistant`能访问储能设备。

- **如何更新BLUETTI集成？**  
  1) 进入HACS管理页面进行更新。
  2) 借助git进行更新
```shell
$ cd /<ha workspaces>/config/custom_components/bluetti
$ git pull
```

# 📮 支持 & 反馈

- GitHub Issues: https://github.com/bluetti-official/bluetti-home-assistant/issues