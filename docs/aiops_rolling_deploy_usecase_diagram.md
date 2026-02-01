# Use Case Diagram: AIOps Rolling Deploy An Toàn

## 1. Tổng quan hệ thống

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     AIOps Rolling Deploy Architecture                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│    ┌──────────┐                                                                 │
│    │  DevOps  │                                                                 │
│    │ Engineer │                                                                 │
│    └────┬─────┘                                                                 │
│         │                                                                       │
│         │ "Lên kế hoạch instance refresh cho ASG"                               │
│         ▼                                                                       │
│    ┌─────────────────────────────────────────┐                                  │
│    │         Amazon Bedrock Agent            │                                  │
│    │  ┌─────────────────────────────────┐    │                                  │
│    │  │   Claude AI (Foundation Model)  │    │                                  │
│    │  │   - Phân tích yêu cầu deploy    │    │                                  │
│    │  │   - Đánh giá rủi ro             │    │                                  │
│    │  │   - Yêu cầu xác nhận nếu cần    │    │                                  │
│    │  │   - Giám sát tiến trình         │    │                                  │
│    │  └─────────────────────────────────┘    │                                  │
│    └────────────────┬────────────────────────┘                                  │
│                     │                                                           │
│                     │ Invoke Action Group                                       │
│                     ▼                                                           │
│    ┌─────────────────────────────────────────┐                                  │
│    │      Lambda: ops-agent-actions          │                                  │
│    │  ┌─────────────────────────────────┐    │                                  │
│    │  │ get_asg_status()                │◄───── Kiểm tra trạng thái ASG        │
│    │  │ execute_instance_refresh()      │◄───── Thực thi rolling deploy        │
│    │  │ get_alb_target_health()         │◄───── Kiểm tra health targets        │
│    │  │ get_infrastructure_snapshot()   │◄───── Snapshot toàn bộ infra         │
│    │  └─────────────────────────────────┘    │                                  │
│    └────────────────┬────────────────────────┘                                  │
│                     │                                                           │
│         ┌───────────┴───────────┬───────────────┐                               │
│         ▼                       ▼               ▼                               │
│    ┌──────────┐           ┌──────────┐    ┌──────────┐                          │
│    │   ASG    │           │   ALB    │    │   EC2    │                          │
│    │Auto Scale│           │  Target  │    │Instances │                          │
│    │  Group   │           │  Groups  │    │          │                          │
│    └──────────┘           └──────────┘    └──────────┘                          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 2. Use Case Diagram (UML)

```
                           ┌─────────────────────────────────────────────────────────┐
                           │                AIOps Rolling Deploy System               │
                           │                                                          │
                           │  ┌─────────────────────────────────────────────────┐    │
                           │  │                                                 │    │
   ┌──────────┐            │  │    (UC1) Lên kế hoạch Rolling Deploy           │    │
   │          │   request  │  │    ─────────────────────────────               │    │
   │  DevOps  │───────────►│  │    Actor: DevOps                               │    │
   │ Engineer │            │  │    Mục đích: Lập kế hoạch deploy an toàn       │    │
   │          │◄───────────│  │    KHÔNG thực thi ngay                         │    │
   └──────────┘   plan     │  │                                                 │    │
                           │  └───────────────┬─────────────────────────────────┘    │
                           │                  │ <<include>>                           │
                           │         ┌────────┴────────┐                              │
                           │         ▼                 ▼                              │
                           │  ┌────────────────┐ ┌────────────────┐                   │
                           │  │(UC2) Kiểm tra  │ │(UC3) Đánh giá  │                   │
                           │  │trạng thái ASG  │ │rủi ro deploy   │                   │
                           │  │hiện tại        │ │                │                   │
                           │  └────────────────┘ └────────────────┘                   │
                           │                                                          │
                           │  ┌─────────────────────────────────────────────────┐    │
   ┌──────────┐            │  │    (UC4) Xác nhận & Thực thi Deploy             │    │
   │          │  confirm   │  │    ─────────────────────────────               │    │
   │  DevOps  │───────────►│  │    Actor: DevOps (phải xác nhận rõ ràng)       │    │
   │ Engineer │            │  │    Mục đích: Trigger Instance Refresh          │    │
   │          │◄───────────│  │    Yêu cầu: Có từ khóa "xác nhận/confirm"      │    │
   └──────────┘  progress  │  │                                                 │    │
                           │  └───────────────┬─────────────────────────────────┘    │
                           │                  │ <<include>>                           │
                           │         ┌────────┴────────┐                              │
                           │         ▼                 ▼                              │
                           │  ┌────────────────┐ ┌────────────────┐                   │
                           │  │(UC5) Execute   │ │(UC6) Giám sát  │                   │
                           │  │Instance        │ │tiến trình      │                   │
                           │  │Refresh         │ │deploy          │                   │
                           │  └────────────────┘ └────────────────┘                   │
                           │                                                          │
                           │  ┌─────────────────────────────────────────────────┐    │
                           │  │    (UC7) Kiểm tra kết quả sau Deploy           │    │
                           │  │    ─────────────────────────────               │    │
                           │  │    - Health check các instances mới            │    │
                           │  │    - Verify ALB target health                  │    │
                           │  │    - Báo cáo kết quả cuối cùng                 │    │
                           │  └─────────────────────────────────────────────────┘    │
                           │                                                          │
                           └─────────────────────────────────────────────────────────┘
```

## 3. Sequence Diagram - Luồng Rolling Deploy An Toàn

```
┌─────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────┐     ┌─────────┐
│ DevOps  │     │Bedrock Agent │     │   Lambda    │     │   ASG   │     │   ALB   │
│Engineer │     │  (Claude)    │     │ops-agent-   │     │         │     │ Target  │
└────┬────┘     └──────┬───────┘     │  actions    │     └────┬────┘     │ Group   │
     │                 │             └──────┬──────┘          │          └────┬────┘
     │                 │                    │                 │               │
     │ ═══════════════════════════════════════════════════════════════════════════
     │ ║ PHASE 1: LẬP KẾ HOẠCH (Planning - Không thực thi)                       ║
     │ ═══════════════════════════════════════════════════════════════════════════
     │                 │                    │                 │               │
     │ 1. "Lên kế     │                    │                 │               │
     │    hoạch       │                    │                 │               │
     │    refresh"    │                    │                 │               │
     │────────────────►                    │                 │               │
     │                 │                    │                 │               │
     │                 │ 2. Nhận diện:     │                 │               │
     │                 │    PLANNING mode  │                 │               │
     │                 │    (không có      │                 │               │
     │                 │    "xác nhận")    │                 │               │
     │                 │                    │                 │               │
     │                 │ 3. get_asg_status │                 │               │
     │                 │───────────────────►                 │               │
     │                 │                    │ 4. Describe ASG│               │
     │                 │                    │────────────────►               │
     │                 │                    │◄────────────────               │
     │                 │                    │ {desired:2,    │               │
     │                 │                    │  running:2,    │               │
     │                 │                    │  healthy:2}    │               │
     │                 │◄───────────────────│                │               │
     │                 │                    │                 │               │
     │                 │ 5. get_alb_target_health            │               │
     │                 │───────────────────►                 │               │
     │                 │                    │ 6. Describe TG │               │
     │                 │                    │─────────────────────────────────►
     │                 │                    │◄─────────────────────────────────
     │                 │                    │ {targets: 2,   │               │
     │                 │                    │  healthy: 2}   │               │
     │                 │◄───────────────────│                │               │
     │                 │                    │                 │               │
     │                 │ 7. AI phân tích   │                 │               │
     │                 │    & đánh giá     │                 │               │
     │                 │    rủi ro         │                 │               │
     │                 │                    │                 │               │
     │ 8. Trả về      │                    │                 │               │
     │    KẾ HOẠCH    │                    │                 │               │
     │◄────────────────│                    │                 │               │
     │ (chưa thực thi)│                    │                 │               │
     │                 │                    │                 │               │
     │ ═══════════════════════════════════════════════════════════════════════════
     │ ║ PHASE 2: XÁC NHẬN & THỰC THI (Execution - Cần approval)                 ║
     │ ═══════════════════════════════════════════════════════════════════════════
     │                 │                    │                 │               │
     │ 9. "Tôi XÁC    │                    │                 │               │
     │    NHẬN: thực  │                    │                 │               │
     │    thi refresh"│                    │                 │               │
     │────────────────►                    │                 │               │
     │                 │                    │                 │               │
     │                 │ 10. Nhận diện:    │                 │               │
     │                 │     EXECUTION mode│                 │               │
     │                 │     (có "xác nhận")                 │               │
     │                 │                    │                 │               │
     │                 │ 11. execute_instance_refresh        │               │
     │                 │───────────────────►                 │               │
     │                 │    {asg_name,     │                 │               │
     │                 │     min_healthy:  │                 │               │
     │                 │     50%}          │                 │               │
     │                 │                    │                 │               │
     │                 │                    │ 12. Start      │               │
     │                 │                    │     Instance   │               │
     │                 │                    │     Refresh    │               │
     │                 │                    │────────────────►               │
     │                 │                    │                 │               │
     │                 │                    │ 13. Refresh    │               │
     │                 │                    │     Started    │               │
     │                 │                    │◄────────────────               │
     │                 │                    │ {refreshId:    │               │
     │                 │                    │  "abc-123"}    │               │
     │                 │                    │                 │               │
     │                 │◄───────────────────│                │               │
     │                 │                    │                 │               │
     │ 14. Thông báo  │                    │                 │               │
     │     đã bắt đầu │                    │                 │               │
     │◄────────────────│                    │                 │               │
     │                 │                    │                 │               │
     │ ═══════════════════════════════════════════════════════════════════════════
     │ ║ PHASE 3: GIÁM SÁT (Monitoring - Tự động/theo yêu cầu)                   ║
     │ ═══════════════════════════════════════════════════════════════════════════
     │                 │                    │                 │               │
     │ 15. "Kiểm tra  │                    │                 │               │
     │     tiến độ"   │                    │                 │               │
     │────────────────►                    │                 │               │
     │                 │                    │                 │               │
     │                 │ 16. get_asg_status│                 │               │
     │                 │───────────────────►                 │               │
     │                 │                    │────────────────►               │
     │                 │                    │◄────────────────               │
     │                 │◄───────────────────│ {refresh:      │               │
     │                 │                    │  InProgress,   │               │
     │                 │                    │  50% done}     │               │
     │                 │                    │                 │               │
     │ 17. Báo cáo    │                    │                 │               │
     │     tiến độ    │                    │                 │               │
     │◄────────────────│                    │                 │               │
     │ "50% hoàn tất" │                    │                 │               │
     │                 │                    │                 │               │
```

## 4. Chi tiết các Use Case

### UC1: Lên kế hoạch Rolling Deploy

| Thuộc tính | Mô tả |
|------------|-------|
| **Actor** | DevOps Engineer |
| **Mục đích** | Lập kế hoạch deploy mới mà KHÔNG thực thi ngay |
| **Trigger** | DevOps hỏi: "Lên kế hoạch refresh" (không có từ "xác nhận") |
| **Precondition** | - ASG đang hoạt động bình thường<br>- Có ít nhất 1 instance healthy |
| **Main Flow** | 1. AI kiểm tra trạng thái ASG hiện tại<br>2. Kiểm tra ALB target health<br>3. Đánh giá rủi ro<br>4. Trả về kế hoạch chi tiết |
| **Postcondition** | DevOps nhận được kế hoạch, HỆ THỐNG CHƯA THAY ĐỔI |

### UC2: Kiểm tra trạng thái ASG

| Thuộc tính | Mô tả |
|------------|-------|
| **Actor** | System (Lambda) |
| **Tool** | `get_asg_status` |
| **Output** | - Desired/Running/Pending instances<br>- Scaling activities gần đây<br>- Instance refresh status (nếu có) |

### UC3: Đánh giá rủi ro deploy

| Thuộc tính | Mô tả |
|------------|-------|
| **Actor** | AI (Claude) |
| **Input** | ASG status, ALB health, current time |
| **Risk Factors** | - Số lượng healthy instances<br>- Có refresh đang chạy không?<br>- Thời điểm deploy (giờ cao điểm?)<br>- % instances sẽ bị terminate |
| **Output** | Risk assessment: LOW / MEDIUM / HIGH |

### UC4: Xác nhận & Thực thi Deploy

| Thuộc tính | Mô tả |
|------------|-------|
| **Actor** | DevOps Engineer |
| **Trigger** | Câu lệnh CÓ từ khóa xác nhận: "Tôi xác nhận", "confirm", "thực thi" |
| **Safety Check** | AI sẽ KHÔNG thực thi nếu không có xác nhận rõ ràng |
| **Main Flow** | 1. AI xác nhận ý định<br>2. Gọi `execute_instance_refresh`<br>3. Trả về refresh ID và trạng thái |

### UC5: Execute Instance Refresh

| Thuộc tính | Mô tả |
|------------|-------|
| **Actor** | System (Lambda → ASG API) |
| **Tool** | `execute_instance_refresh` |
| **Parameters** | - `asg_name`: Tên Auto Scaling Group<br>- `min_healthy_percentage`: % instance phải healthy (default: 50%) |
| **AWS API** | `start_instance_refresh()` |

### UC6: Giám sát tiến trình deploy

| Thuộc tính | Mô tả |
|------------|-------|
| **Actor** | DevOps Engineer (theo yêu cầu) |
| **Tool** | `get_asg_status` |
| **Monitored Items** | - Refresh percentage complete<br>- Instances being replaced<br>- Any failures |

### UC7: Kiểm tra kết quả sau Deploy

| Thuộc tính | Mô tả |
|------------|-------|
| **Actor** | DevOps Engineer |
| **Verification** | - Tất cả instances mới đã healthy?<br>- ALB targets đã registered?<br>- Application responding correctly? |

## 5. Ví dụ Conversation Flow

### 🔵 PHASE 1: Planning (An toàn - không thay đổi gì)

**DevOps hỏi:**
```
Lên kế hoạch instance refresh cho ASG nhưng chưa thực thi
```

**AIOps trả lời:**
```
📋 KẾ HOẠCH INSTANCE REFRESH

🔍 TRẠNG THÁI HIỆN TẠI:
┌─────────────────────────────────────────────────────┐
│ ASG: course-management-asg-dev                      │
├─────────────────────────────────────────────────────┤
│ Desired Capacity  : 2                               │
│ Running Instances : 2                               │
│ Healthy Instances : 2 ✅                            │
│ Pending Instances : 0                               │
│ Active Refresh    : None                            │
└─────────────────────────────────────────────────────┘

🎯 ALB TARGET HEALTH:
┌─────────────────────────────────────────────────────┐
│ Target Group: course-management-tg-dev              │
├─────────────────────────────────────────────────────┤
│ Total Targets     : 2                               │
│ Healthy           : 2 ✅                            │
│ Unhealthy         : 0                               │
│ Draining          : 0                               │
└─────────────────────────────────────────────────────┘

⚠️ ĐÁNH GIÁ RỦI RO: THẤP ✅
- Tất cả instances đều healthy
- Không có refresh nào đang chạy
- Hệ thống ổn định

📝 KẾ HOẠCH THỰC THI:
1. Instance Refresh sẽ thay thế từng instance một
2. Min healthy percentage: 50% (ít nhất 1 instance luôn chạy)
3. Thời gian ước tính: ~10-15 phút
4. Downtime: KHÔNG (rolling update)

⚡ ĐỂ THỰC THI, VUI LÒNG XÁC NHẬN:
Gõ: "Tôi xác nhận: thực thi instance refresh cho ASG course-management-asg-dev"
```

---

### 🟢 PHASE 2: Execution (Cần xác nhận rõ ràng)

**DevOps xác nhận:**
```
Tôi xác nhận: hãy thực thi instance refresh cho ASG course-management-asg-dev
```

**AIOps trả lời:**
```
🚀 BẮT ĐẦU INSTANCE REFRESH

✅ Instance Refresh đã được khởi tạo thành công!

┌─────────────────────────────────────────────────────┐
│ Refresh ID        : abc123-def456-ghi789            │
│ ASG Name          : course-management-asg-dev       │
│ Status            : Pending → InProgress            │
│ Min Healthy %     : 50%                             │
│ Started At        : 2025-12-25 15:30:00 UTC         │
└─────────────────────────────────────────────────────┘

📊 TIẾN TRÌNH:
[░░░░░░░░░░░░░░░░░░░░] 0% - Đang bắt đầu...

🔔 THEO DÕI:
- Gõ "Kiểm tra tiến độ refresh" để xem trạng thái
- Refresh sẽ tự động thay thế từng instance
- Ước tính hoàn thành: ~10-15 phút
```

---

### 🟡 PHASE 3: Monitoring

**DevOps hỏi:**
```
Kiểm tra tiến độ refresh
```

**AIOps trả lời:**
```
📊 TIẾN ĐỘ INSTANCE REFRESH

┌─────────────────────────────────────────────────────┐
│ Refresh ID  : abc123-def456-ghi789                  │
│ Status      : InProgress                            │
│ Progress    : 50%                                   │
└─────────────────────────────────────────────────────┘

[██████████░░░░░░░░░░] 50%

📋 CHI TIẾT:
- Instance i-old-001: ⏳ Đang terminate
- Instance i-new-001: ✅ Healthy, serving traffic
- Instance i-old-002: 🔄 Đợi thay thế

⏱️ Ước tính hoàn thành: ~5 phút nữa
```

---

### ✅ PHASE 4: Completion

**AIOps báo hoàn thành:**
```
🎉 INSTANCE REFRESH HOÀN TẤT!

┌─────────────────────────────────────────────────────┐
│ Status            : Successful ✅                   │
│ Duration          : 12 phút 34 giây                 │
│ Instances Updated : 2/2                             │
└─────────────────────────────────────────────────────┘

📊 TRẠNG THÁI SAU DEPLOY:
┌─────────────────────────────────────────────────────┐
│ Instance           │ Status   │ Health │ Age       │
├────────────────────┼──────────┼────────┼───────────┤
│ i-new-001          │ Running  │ ✅     │ 12m       │
│ i-new-002          │ Running  │ ✅     │ 6m        │
└─────────────────────────────────────────────────────┘

🎯 ALB TARGET HEALTH: 2/2 Healthy ✅

💡 KHUYẾN NGHỊ:
- Monitor application logs trong 15 phút tiếp
- Kiểm tra metrics (latency, error rate)
- Nếu có vấn đề, có thể rollback bằng cách deploy lại AMI cũ
```

## 6. Safety Mechanisms (Cơ chế an toàn)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          SAFETY MECHANISMS                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ 1️⃣  TWO-PHASE CONFIRMATION                                              │    │
│  │                                                                          │    │
│  │    Planning Phase          Execution Phase                               │    │
│  │    ┌──────────────┐        ┌──────────────┐                              │    │
│  │    │ "Lên kế      │   ≠    │ "Xác nhận    │                              │    │
│  │    │  hoạch..."   │        │  thực thi"   │                              │    │
│  │    └──────┬───────┘        └──────┬───────┘                              │    │
│  │           │                       │                                      │    │
│  │           ▼                       ▼                                      │    │
│  │    [Read-only ops]         [Write ops]                                   │    │
│  │    - get_asg_status        - execute_instance_refresh                    │    │
│  │    - get_alb_health        - (requires explicit confirm)                 │    │
│  │                                                                          │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ 2️⃣  KEYWORD DETECTION                                                   │    │
│  │                                                                          │    │
│  │    Trigger Words for Execution:                                          │    │
│  │    ┌────────────────────────────────────────────┐                        │    │
│  │    │ ✅ "Tôi xác nhận"                          │                        │    │
│  │    │ ✅ "I confirm"                             │                        │    │
│  │    │ ✅ "Thực thi ngay"                         │                        │    │
│  │    │ ✅ "Execute now"                           │                        │    │
│  │    │ ✅ "Proceed with refresh"                  │                        │    │
│  │    └────────────────────────────────────────────┘                        │    │
│  │                                                                          │    │
│  │    Without these → AI only returns PLAN, no action                       │    │
│  │                                                                          │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ 3️⃣  MIN HEALTHY PERCENTAGE                                              │    │
│  │                                                                          │    │
│  │    ASG Instance Refresh Config:                                          │    │
│  │    ┌────────────────────────────────────────────┐                        │    │
│  │    │ min_healthy_percentage: 50%                │                        │    │
│  │    │                                            │                        │    │
│  │    │ → Luôn giữ ít nhất 50% instances healthy   │                        │    │
│  │    │ → Với 2 instances: 1 luôn serving traffic  │                        │    │
│  │    │ → Zero downtime deployment                 │                        │    │
│  │    └────────────────────────────────────────────┘                        │    │
│  │                                                                          │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ 4️⃣  PRE-FLIGHT CHECKS                                                   │    │
│  │                                                                          │    │
│  │    Before executing refresh, AI verifies:                                │    │
│  │    ┌────────────────────────────────────────────┐                        │    │
│  │    │ ☑️ No active refresh running                │                       │    │
│  │    │ ☑️ All current instances healthy            │                       │    │
│  │    │ ☑️ ALB targets responding                   │                       │    │
│  │    │ ☑️ ASG not in scaling activity              │                       │    │
│  │    └────────────────────────────────────────────┘                        │    │
│  │                                                                          │    │
│  │    If any check fails → AI warns and suggests waiting                    │    │
│  │                                                                          │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 7. Component Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                 AWS Cloud                                     │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                         Amazon Bedrock                                   │ │
│  │  ┌───────────────────┐    ┌──────────────────────────────────────────┐  │ │
│  │  │   Agent           │    │        Action Group                       │  │ │
│  │  │  (CGWF5H93V2)     │───►│  ┌─────────────────────────────────────┐  │  │ │
│  │  │                   │    │  │     OpenAPI Schema                   │  │  │ │
│  │  │  - Claude 3.5     │    │  │  ┌─────────────────────────────────┐ │  │  │ │
│  │  │  - Understand     │    │  │  │ /get_asg_status              ◄──┼─┼──READ
│  │  │    intent         │    │  │  │ /get_alb_target_health       ◄──┼─┼──READ
│  │  │  - Safety check   │    │  │  │ /execute_instance_refresh    ◄──┼─┼──WRITE
│  │  │                   │    │  │  │ /get_infrastructure_snapshot ◄──┼─┼──READ
│  │  └───────────────────┘    │  │  └─────────────────────────────────┘ │  │  │ │
│  │                           │  └─────────────────────────────────────┘  │  │ │
│  │                           └──────────────────┬───────────────────────┘  │ │
│  └──────────────────────────────────────────────┼──────────────────────────┘ │
│                                                 │                            │
│                                                 ▼                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                         AWS Lambda                                       │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │ │
│  │  │                  ops-agent-actions                                 │  │ │
│  │  │                                                                    │  │ │
│  │  │  ┌────────────────────────────────────────────────────────────┐   │  │ │
│  │  │  │            execute_instance_refresh()                       │   │  │ │
│  │  │  │                                                             │   │  │ │
│  │  │  │  1. Validate ASG name exists                                │   │  │ │
│  │  │  │  2. Check no active refresh                                 │   │  │ │
│  │  │  │  3. Call ASG start_instance_refresh()                       │   │  │ │
│  │  │  │  4. Return refresh ID and status                            │   │  │ │
│  │  │  │                                                             │   │  │ │
│  │  │  └────────────────────────────────────────────────────────────┘   │  │ │
│  │  └───────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│         ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    │
│         │  Auto Scaling   │    │      ALB        │    │      EC2        │    │
│         │     Group       │    │  Target Group   │    │   Instances     │    │
│         │                 │    │                 │    │                 │    │
│         │ - Desired: 2    │    │ - Healthy: 2    │    │ - i-abc123      │    │
│         │ - Min: 1        │    │ - Draining: 0   │    │ - i-def456      │    │
│         │ - Max: 4        │    │                 │    │                 │    │
│         └────────┬────────┘    └────────┬────────┘    └────────┬────────┘    │
│                  │                      │                      │             │
│                  └──────────────────────┴──────────────────────┘             │
│                              Instance Refresh Flow:                          │
│                     1. Launch new instance                                   │
│                     2. Wait for health check                                 │
│                     3. Register to ALB                                       │
│                     4. Drain old instance                                    │
│                     5. Terminate old instance                                │
│                     6. Repeat for next instance                              │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 8. Prompt Cheat Sheet

| Mục đích | Prompt | Loại |
|----------|--------|------|
| Xem kế hoạch | `Lên kế hoạch instance refresh cho ASG nhưng chưa thực thi` | 📖 READ |
| Kiểm tra ASG | `Kiểm tra trạng thái ASG hiện tại` | 📖 READ |
| Kiểm tra ALB | `Kiểm tra health của ALB targets` | 📖 READ |
| Thực thi refresh | `Tôi xác nhận: thực thi instance refresh cho ASG <tên>` | ✏️ WRITE |
| Theo dõi tiến độ | `Kiểm tra tiến độ instance refresh` | 📖 READ |
| Snapshot toàn bộ | `Kiểm tra infrastructure hiện tại` | 📖 READ |

## 9. Glossary (Thuật ngữ)

| Thuật ngữ | Giải thích |
|-----------|------------|
| **ASG** | Auto Scaling Group - Nhóm EC2 instances tự động scale |
| **Instance Refresh** | Tính năng AWS thay thế instances từng cái một (rolling) |
| **Rolling Deploy** | Deploy không downtime, thay từng instance một |
| **ALB** | Application Load Balancer - Cân bằng tải layer 7 |
| **Target Group** | Nhóm các EC2 instances phục vụ traffic từ ALB |
| **Health Check** | Kiểm tra instance còn hoạt động không |
| **Draining** | Đang chờ kết thúc connections trước khi terminate |
| **Min Healthy %** | % instances tối thiểu phải healthy trong quá trình refresh |

---

**Document Version**: 1.0  
**Created**: 2025-12-25  
**Author**: AIOps System Documentation
