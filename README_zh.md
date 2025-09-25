# BLUETTI储能HA集成

[English](./README.md) | [简体中文](./README_zh.md)

BLUETTI储能集成是一个由BLUETTI官方提供的Home Assistant集成插件，支持在Home Assistant系统中使用您的BLUETTI智能储能设备。

BLUETTI储能集成github仓库地址：https://github.com/bluetti-official/bluetti-home-assistant

# ✨ 功能特性

- ✅ 设备运行状态（Inverter Status）  
- ✅ 查询电量SOC（Battery Level）  
- ✅ 预估续航时间（Charge Full Time）
- ✅ AC / DC 开关（AC Switch，DC Switch）  
- ✅ 整机电源开关（Power）  
- ✅ 工作模式切换（Working Mode）：自发自用，备用电源，削峰填谷
- ✅ ECO模式切换（AC ECO，DC ECO）  
- ✅ 灾害预警功能（Disaster Warning）  

# 🎮 机型支持清单


|        | 设备<br/>运行状态 | 查询<br/>电量SOC | 预估<br/>续航时间 | AC/DC开关 | 整机电源开关 | 工作模式切换 | ECO模式切换 | 灾害预警功能 |
|--------|--------|---------|--------|---------|--------|--------|---------|--------|
| EP13K  | ✅      | ✅       | ✅      |         | ✅      | ✅      |         | ✅      |
| EP6K   | ✅      | ✅       | ✅      |         | ✅      | ✅      |         | ✅      |
| EP2000 | ✅      | ✅       | ✅      |         | ✅      | ✅      |         | ✅      |
| FP     | ✅      | ✅       | ✅      | ✅       | ✅      | ✅      | ✅       | ✅      |
 
# 📦 安装方法

## 方法A：手动安装

1. 进入Home Assistant配置目录：
```shell
$ cd /<ha workspaces>/core/config/custom_components
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
<hr/>

# ⚙️ 配置集成

## 通过界面添加集成

1. 进入`Home Assistant` → 设置 → 设备与服务；  
   <img src="./doc/images/1-setting_devices_and_services.png">
2. 搜索并选择`BLUETTI`
3. 链接BLUETTI APP账号，使用OAUTH授权登录。

BLUETTI储能集成是UI配置型（config flow），非configuration.yaml文件配置的方式，所以用户只需要通过BLUETTI集成的授权登录页面输入用户在Bluetti APP上注册的账号密码即可。