# Blood Test OCR & AI Interpretation

*[Read in English](README.md)*

## Proje Hakkında

Bu proje, bir kan tahlili raporu görüntüsünü otomatik olarak okuyup
yorumlayan bir web uygulamasıdır. Kullanıcı bir kan tahlili görüntüsü
yükler; sistem OCR ile test sonuçlarını çıkarır, her değerin normal
aralıkta olup olmadığını belirler ve yerel bir yapay zeka modeli
aracılığıyla anlaşılır bir açıklama üretir.

> **Not:** Bu uygulama tıbbi tanı koymaz. Ürettiği yorumlar yalnızca
> bilgilendirme amaçlıdır; kesin sonuç için bir doktora danışılmalıdır.

## 🎥 Demo



https://github.com/user-attachments/assets/c38875eb-15a4-4aba-b6f6-0690ef46b3dd



## Kullanılan Teknolojiler

- **Python 3**
- **Streamlit** — web arayüzü
- **Azure AI Document Intelligence** — görüntüden tablo verisi çıkarma (OCR)
- **Foundry Local (Phi-4-mini)** — sonuçları yorumlayan yerel dil modeli

## Proje Yapısı

```
analiz/
├── app.py               # Streamlit arayüzü (yükleme, tablo, sohbet)
├── llm_analysis.py       # LLM ile yorum üretme ve sohbet akışı
├── ocr_analysis.py       # Azure Document Intelligence ile OCR işlemi
├── data_process.py       # OCR verisini işleme ve durum (low/high/normal) belirleme
├── .env                  # Azure bağlantı bilgileri (ocr_endpoint, ocr_key)
└── README.md
```

## Nasıl Çalışır?

1. Kullanıcı, **OCR Results** sekmesinden bir kan tahlili görüntüsü yükler.
2. **Analyze** butonuna basıldığında görüntü Azure Document Intelligence'a
   gönderilir ve tablodaki test sonuçları (test adı, değer, birim, referans
   aralığı) çıkarılır.
3. Her test sonucu, referans aralığıyla karşılaştırılarak **Low / High /
   Normal** olarak sınıflandırılır ve sağ tarafta bir tabloda gösterilir.
4. Kullanıcı **AI Interpretation & Q&A** sekmesine geçip **Generate
   Interpretation** butonuna basınca, sonuçlar yerel bir dil modeline
   (Phi-4-mini) gönderilir; model her test için ne olduğunu, olası
   nedenlerini ve önerilerini açıklar.
5. Kullanıcı, bu ilk değerlendirmenin ardından sonuçlarla ilgili serbestçe
   soru sorabilir (örn. *"what is hemoglobin?"*).

## Kurulum

```bash
python -m venv venv
venv\Scripts\activate

python -m pip install streamlit azure-ai-documentintelligence foundry-local-sdk python-dotenv
```

Proje klasöründe bir `.env` dosyası oluşturup Azure Document Intelligence
bilgilerini gir:

```
ocr_endpoint=https://<kaynak-adin>.cognitiveservices.azure.com/
ocr_key=<senin-key'in>
```

## Kullanım

```bash
streamlit run app.py
```

Uygulama açıldığında:
1. **OCR Results** sekmesinden bir rapor görüntüsü yükle, **Analyze**'e bas.
2. Çıkarılan test sonuçlarını (durum etiketleriyle birlikte) tabloda incele.
3. **AI Interpretation & Q&A** sekmesine geçip **Generate Interpretation**
   ile genel değerlendirmeyi al.
4. Sonuçlarla ilgili ek sorular sor.

## Durum Belirleme Mantığı

Her test sonucunun durumu (`low` / `high` / `normal`) modele bırakılmaz,
kod tarafında belirlenir:

1. Rapor zaten `[H]` / `[L]` işareti koymuşsa, bu işarete güvenilir.
2. İşaret yoksa, değer ve referans aralığı sayıya çevrilip doğrudan
   karşılaştırılır.
3. Değer veya aralık standart formatta değilse durum `unknown` olarak
   işaretlenir.

Bu ayrım bilinçlidir: durum belirleme her zaman deterministik koddan
gelir, yorumlama ve öneri ise dil modelinden — bu, modelin sayısal
karşılaştırmada hata yapma riskini ortadan kaldırır.

## Sınırlamalar

- Yalnızca tablo formatındaki raporlarda güvenilir çalışır.
- Referans aralığı standart (`min-max`) formatta değilse durum
  belirlenemeyebilir (`unknown` olarak işaretlenir).
- Görüntü kalitesi düşükse OCR bazı değerleri yanlış okuyabilir.
- Sonuçlar kalıcı olarak saklanmaz; her oturumda rapor yeniden işlenir.
