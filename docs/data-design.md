# AccessGuard 数据结构设计

## 1. 项目说明

AccessGuard 是一个基于 Redis 的访问监控与风控练习项目。

项目目标是模拟 Web 服务访问日志处理，对访问 IP 进行统计、记录、风险评分和临时封禁。

本项目主要用于练习 Redis 常见数据结构的实际使用场景，包括：

- String
- Hash
- List
- Set
- ZSet
- TTL


## 2. key设计总览
| 功能 | Key 设计 | 数据类型 | 作用 |
|---|---|---|---|
| IP 访问统计 | `ip:{ip}:count:{date}` | String | 记录某个 IP 当天访问次数 |
| IP 信息记录 | `ip:{ip}:info` | Hash | 记录某个 IP 的基础访问信息 |
| IP 日志记录 | `ip:{ip}:logs` | List | 保存某个 IP 最近访问日志 |
| 活跃 IP 记录 | `active:ip:{date}` | Set | 记录当天出现过的 IP，自动去重 |
| 风险排行榜 | `risk:rank:{date}` | ZSet | 按风险分对 IP 进行排序 |
| 封禁 IP 记录 | `ban:ip:{ip}` | String + TTL | 临时封禁高风险 IP |

### 2.1 IP访问统计
	类型-key
	示例-ip:10.0.0.1:count:2026-04-27
	用途-记录某个IP在某一天的访问次数
	操作命令-INCR ip:{ip}:count:{date}
		 GET ip:{ip}:count:{date}
	TTL-建议保留7天或30天

### 2.2 IP信息记录
        类型-hash
        示例-ip:10.0.0.1:info
	字段设计 
		- first_seen：首次访问时间
		- last_seen：最近访问时间
		- last_path：最近访问路径
		- last_status：最近状态码
	用途-记录单个 IP 的基础访问信息
	操作命令-HSETNX ip:{ip}:info first_seen {time}
		-HSET ip:{ip}:info last_seen {time} last_path {path} last_status {status}
		-HGETALL ip:{ip}:info

### 2.3 IP日志记录
	类型-List
	示例-ip:10.0.0.1:logs
	用途-记录某个IP最近的访问日志
	操作命令-LPUSH ip:{ip}:logs "{time} {method} {path} {status}"
		-LTRIM ip:{ip}:logs 0 9
		-LRANGE ip:{ip}:logs 0 9
	TTL-可选

### 2.4 活跃IP记录
        类型-Set
        示例-active:ip:2026-04-27
        用途-记录某一天访问过系统的IP，自动去重
        操作命令-SADD active:ip:{date} {ip}
		-SCARD active:ip:{date}
		-SMEMBERS active:ip:{date}
	TTL-建议保留7天

### 2.5 风险排行榜
        类型-ZSet
        示例-risk:rank:2026-04-27
        用途-记录某一天IP的风险分数，并按照分数排序
        操作命令-ZINCRBY risk:rank:{date} {score} {ip}
		-ZSCORE risk:rank:{date} {ip}
		-ZREVRANGE risk:rank:{date} 0 9 WITHSCORES
	TTL-建议保留7天或30天

### 2.6 封禁IP记录
        类型-String + TTL
        示例-ban:ip:10.0.0.1
        用途-记录临时封禁IP
        操作命令-SET ban:ip:{ip} 1 EX 60
		-GET ban:ip:{ip}
		-TTL ban:ip:{ip}
	TTL-第一阶段设计为60秒
