package org.insightcentre.lodcloud;
import java.util.HashMap;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import java.util.Set;
import java.util.Map;
import java.io.IOException;
import com.fasterxml.jackson.databind.JsonSerializer;
import com.fasterxml.jackson.databind.ser.std.StdSerializer;
import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.databind.SerializerProvider;
import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.annotation.JsonDeserialize;
import com.fasterxml.jackson.databind.JsonDeserializer;
import com.fasterxml.jackson.databind.deser.std.StdDeserializer;
import com.fasterxml.jackson.databind.DeserializationContext;
import com.fasterxml.jackson.core.JsonParser;

@JsonSerialize(using = Document.DocumentSerializer.class)
@JsonDeserialize(using = Document.DocumentDeserializer.class)
public class Document {
    private Map<String,Object> data = new HashMap<>();
    
    public Document() {
    }
    
    public Document(Map<String,Object> data) {
        this.data = data;
    }

    public void put(String key, Object value) {
        data.put(key, value);
    }
    
    public Object get(String key) {
        return data.get(key);
    }

    public <V> V get(String key, V defaultValue) {
        Object o = data.get(key);
        if(o == null) {
            return defaultValue;
        } else {
            return (V)o;
        }
    }

    public String toJson() {
        try {
            return new ObjectMapper().writeValueAsString(data);
        } catch(JsonProcessingException x) {
            throw new RuntimeException(x);
        }
    }

    public String toPrettyJson() {
        try {
            return new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(data);
        } catch(JsonProcessingException x) {
            throw new RuntimeException(x);
        }
    }

    public Set<Map.Entry<String,Object>> entrySet() {
        return data.entrySet();
    }

    public boolean containsKey(String key) {
        return data.containsKey(key);
    }

    public static Document parse(String jsonString) throws IOException {
        try {
            return new Document(new ObjectMapper().readValue(jsonString, HashMap.class));
        } catch(JsonProcessingException x) {
            throw new RuntimeException(x);
        }
    }

    public static class DocumentSerializer extends StdSerializer<Document> {
        public DocumentSerializer() {
            super(Document.class);
        }

        @Override
        public void serialize(Document value, JsonGenerator gen, SerializerProvider provider) throws IOException {
            gen.writeObject(value.data);
        }
    }

    public static class DocumentDeserializer extends StdDeserializer<Document> {
        public DocumentDeserializer() {
            super(Document.class);
        }

        @Override
        public Document deserialize(JsonParser gen, DeserializationContext ctxt) throws IOException {
            return new Document(gen.readValueAs(HashMap.class));
        }
    }
}
