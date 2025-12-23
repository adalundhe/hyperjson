#!/usr/bin/env python3
"""Benchmark comparison between original orjson and our subinterpreter-compatible version."""

import time
import sys
import importlib
import random
import string
import json
import subprocess
import glob
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from uuid import uuid4


@dataclass
class Address:
    street: str
    city: str
    state: str
    zip_code: str
    country: str


@dataclass
class Person:
    id: str
    name: str
    age: int
    email: str
    active: bool
    address: Address
    tags: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None


def create_complex_structure() -> Dict[str, Any]:
    """Create a complex, realistic JSON-serializable structure."""
    persons = []
    for i in range(50):
        person = Person(
            id=str(uuid4()),
            name=f"Person {i}",
            age=20 + (i % 60),
            email=f"person{i}@example.com",
            active=i % 3 != 0,
            address=Address(
                street=f"{100 + i} Main St",
                city=["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"][i % 5],
                state=["NY", "CA", "IL", "TX", "AZ"][i % 5],
                zip_code=f"{10000 + i:05d}",
                country="USA"
            ),
            tags=[f"tag{j}" for j in range(i % 5)],
            metadata={
                "score": 85.5 + (i % 20),
                "level": i % 10,
                "preferences": {
                    "theme": "dark" if i % 2 == 0 else "light",
                    "notifications": i % 3 == 0,
                    "language": ["en", "es", "fr"][i % 3]
                },
                "history": [j for j in range(i % 10)]
            },
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc) if i % 2 == 0 else None
        )
        persons.append(person)
    
    structure = {
        "version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "total_count": len(persons),
            "active_count": sum(1 for p in persons if p.active),
            "tags": list(set(tag for p in persons for tag in p.tags)),
            "cities": list(set(p.address.city for p in persons)),
            "nested": {
                "level1": {
                    "level2": {
                        "level3": {
                            "data": [i for i in range(100)],
                            "strings": [f"string_{i}" for i in range(50)],
                            "mixed": [
                                {"id": i, "value": i * 1.5, "active": i % 2 == 0}
                                for i in range(30)
                            ]
                        }
                    }
                }
            }
        },
        "persons": [
            {
                "id": p.id,
                "name": p.name,
                "age": p.age,
                "email": p.email,
                "active": p.active,
                "address": {
                    "street": p.address.street,
                    "city": p.address.city,
                    "state": p.address.state,
                    "zip_code": p.address.zip_code,
                    "country": p.address.country
                },
                "tags": p.tags,
                "metadata": p.metadata,
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat() if p.updated_at else None
            }
            for p in persons
        ],
        "statistics": {
            "age_distribution": {
                "20-30": sum(1 for p in persons if 20 <= p.age < 30),
                "30-40": sum(1 for p in persons if 30 <= p.age < 40),
                "40-50": sum(1 for p in persons if 40 <= p.age < 50),
                "50+": sum(1 for p in persons if p.age >= 50)
            },
            "by_state": {
                state: sum(1 for p in persons if p.address.state == state)
                for state in set(p.address.state for p in persons)
            }
        }
    }
    
    return structure


def generate_random_json_object(max_depth: int = 3, current_depth: int = 0) -> Dict[str, Any]:
    """
    Generate a random, valid JSON object with random keys and values.
    This is designed to test performance when caches are ineffective.
    """
    if current_depth >= max_depth:
        # Leaf node - return primitive value
        value_type = random.choice(['string', 'number', 'boolean', 'null'])
        if value_type == 'string':
            # Random string of 10-50 characters
            length = random.randint(10, 50)
            return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
        elif value_type == 'number':
            # Random number (int or float)
            if random.random() < 0.5:
                return random.randint(-1000000, 1000000)
            else:
                return round(random.uniform(-1000000.0, 1000000.0), 2)
        elif value_type == 'boolean':
            return random.choice([True, False])
        else:  # null
            return None
    
    # Generate a dictionary with 3-8 random keys
    num_keys = random.randint(3, 8)
    obj = {}
    
    for _ in range(num_keys):
        # Generate random key (8-20 characters, using random characters)
        key_length = random.randint(8, 20)
        key = ''.join(random.choices(string.ascii_letters + string.digits + '_', k=key_length))
        
        # Generate random value (can be primitive or nested structure)
        if random.random() < 0.3 and current_depth < max_depth - 1:
            # 30% chance of nested object
            obj[key] = generate_random_json_object(max_depth, current_depth + 1)
        elif random.random() < 0.2 and current_depth < max_depth - 1:
            # 20% chance of array
            array_length = random.randint(2, 8)
            obj[key] = [
                generate_random_json_object(max_depth, current_depth + 1)
                for _ in range(array_length)
            ]
        else:
            # 50% chance of primitive value
            value_type = random.choice(['string', 'number', 'boolean', 'null'])
            if value_type == 'string':
                length = random.randint(10, 50)
                obj[key] = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
            elif value_type == 'number':
                if random.random() < 0.5:
                    obj[key] = random.randint(-1000000, 1000000)
                else:
                    obj[key] = round(random.uniform(-1000000.0, 1000000.0), 2)
            elif value_type == 'boolean':
                obj[key] = random.choice([True, False])
            else:  # null
                obj[key] = None
    
    return obj


def benchmark_orjson(orjson_module, name: str, data: Dict[str, Any], iterations: int = 10000):
    """Benchmark serialization and deserialization."""
    print(f"\n{'='*60}")
    print(f"Benchmarking: {name}")
    print(f"{'='*60}")
    
    # Warm-up
    for _ in range(100):
        orjson_module.dumps(data)
        orjson_module.loads(orjson_module.dumps(data))
    
    # Serialization benchmark
    serialized = None
    start = time.perf_counter()
    for _ in range(iterations):
        serialized = orjson_module.dumps(data)
    serialize_time = time.perf_counter() - start
    
    # Deserialization benchmark
    start = time.perf_counter()
    for _ in range(iterations):
        orjson_module.loads(serialized)
    deserialize_time = time.perf_counter() - start
    
    # Round-trip benchmark
    start = time.perf_counter()
    for _ in range(iterations):
        result = orjson_module.loads(orjson_module.dumps(data))
    roundtrip_time = time.perf_counter() - start
    
    serialize_ops_per_sec = iterations / serialize_time
    deserialize_ops_per_sec = iterations / deserialize_time
    roundtrip_ops_per_sec = iterations / roundtrip_time
    
    print(f"Serialization:")
    print(f"  Time: {serialize_time:.4f}s")
    print(f"  Operations/sec: {serialize_ops_per_sec:,.0f}")
    print(f"  Avg time per op: {(serialize_time/iterations)*1e6:.2f}μs")
    
    print(f"\nDeserialization:")
    print(f"  Time: {deserialize_time:.4f}s")
    print(f"  Operations/sec: {deserialize_ops_per_sec:,.0f}")
    print(f"  Avg time per op: {(deserialize_time/iterations)*1e6:.2f}μs")
    
    print(f"\nRound-trip:")
    print(f"  Time: {roundtrip_time:.4f}s")
    print(f"  Operations/sec: {roundtrip_ops_per_sec:,.0f}")
    print(f"  Avg time per op: {(roundtrip_time/iterations)*1e6:.2f}μs")
    
    print(f"\nSerialized size: {len(serialized):,} bytes")
    
    return {
        'name': name,
        'serialize_time': serialize_time,
        'deserialize_time': deserialize_time,
        'roundtrip_time': roundtrip_time,
        'serialize_ops_per_sec': serialize_ops_per_sec,
        'deserialize_ops_per_sec': deserialize_ops_per_sec,
        'roundtrip_ops_per_sec': roundtrip_ops_per_sec,
        'serialized_size': len(serialized)
    }


def main():
    # Check if random benchmark is requested
    run_random = len(sys.argv) > 1 and (sys.argv[1].lower() == '--random-only' or sys.argv[1].lower() == '--random')
    
    if run_random:
        # Random benchmark
        print("\n" + "="*80)
        print("RANDOM OBJECT BENCHMARK (Cache-unfriendly, 10k iterations)")
        print("="*80)
        
        print("\nThis benchmark generates random JSON objects with random keys and values.")
        print("This tests performance when caches are ineffective (cache misses expected).")
        
        random_iterations = 10000
        print(f"\nUsing {random_iterations:,} iterations with fresh random objects per iteration")
        print("Each object is 1-5 KB with 3-8 random keys and nested structures")
        
        # Benchmark random objects with original orjson
        print("\n" + "="*60)
        print("Testing ORIGINAL orjson (PyPI 3.11.4) - Random Objects")
        print("="*60)
        orig_result = None
        try:
            # Clear any cached imports
            if 'orjson' in sys.modules:
                del sys.modules['orjson']
            import orjson as orjson_original
            
            # Generate a sample to show size
            sample_obj = generate_random_json_object()
            sample_json = json.dumps(sample_obj)
            sample_size = len(sample_json.encode('utf-8'))
            print(f"\nSample random object size: {sample_size:,} bytes ({sample_size/1024:.2f} KB)")
            
            # Benchmark with random objects generated on-the-fly
            print("\nGenerating fresh random objects for each iteration...")
            
            # Warm-up
            warmup_iterations = min(100, random_iterations // 100)
            for _ in range(warmup_iterations):
                test_obj = generate_random_json_object()
                serialized = orjson_original.dumps(test_obj)
                _ = orjson_original.loads(serialized)
            
            # Serialization benchmark
            serialize_start = time.perf_counter()
            total_serialized_size = 0
            for _ in range(random_iterations):
                test_obj = generate_random_json_object()
                serialized = orjson_original.dumps(test_obj)
                total_serialized_size += len(serialized)
            serialize_time = time.perf_counter() - serialize_start
            
            # Deserialization benchmark (need to serialize first to get bytes)
            test_objects_serialized = []
            for _ in range(random_iterations):
                test_obj = generate_random_json_object()
                test_objects_serialized.append(orjson_original.dumps(test_obj))
            
            deserialize_start = time.perf_counter()
            for serialized in test_objects_serialized:
                _ = orjson_original.loads(serialized)
            deserialize_time = time.perf_counter() - deserialize_start
            
            # Round-trip benchmark
            roundtrip_start = time.perf_counter()
            for _ in range(random_iterations):
                test_obj = generate_random_json_object()
                serialized = orjson_original.dumps(test_obj)
                _ = orjson_original.loads(serialized)
            roundtrip_time = time.perf_counter() - roundtrip_start
            
            serialize_ops_per_sec = random_iterations / serialize_time
            deserialize_ops_per_sec = random_iterations / deserialize_time
            roundtrip_ops_per_sec = random_iterations / roundtrip_time
            
            print(f"\nSerialization:")
            print(f"  Time: {serialize_time:.4f}s")
            print(f"  Operations/sec: {serialize_ops_per_sec:,.0f}")
            print(f"  Avg time per op: {(serialize_time/random_iterations)*1e6:.2f}μs")
            
            print(f"\nDeserialization:")
            print(f"  Time: {deserialize_time:.4f}s")
            print(f"  Operations/sec: {deserialize_ops_per_sec:,.0f}")
            print(f"  Avg time per op: {(deserialize_time/random_iterations)*1e6:.2f}μs")
            
            print(f"\nRound-trip:")
            print(f"  Time: {roundtrip_time:.4f}s")
            print(f"  Operations/sec: {roundtrip_ops_per_sec:,.0f}")
            print(f"  Avg time per op: {(roundtrip_time/random_iterations)*1e6:.2f}μs")
            
            print(f"\nAvg serialized size: {total_serialized_size / random_iterations:.0f} bytes")
            
            orig_result = {
                'name': 'Original orjson (PyPI 3.11.4) - Random',
                'serialize_time': serialize_time,
                'deserialize_time': deserialize_time,
                'roundtrip_time': roundtrip_time,
                'serialize_ops_per_sec': serialize_ops_per_sec,
                'deserialize_ops_per_sec': deserialize_ops_per_sec,
                'roundtrip_ops_per_sec': roundtrip_ops_per_sec,
                'serialized_size': total_serialized_size // random_iterations
            }
        except Exception as e:
            print(f"Error loading original orjson: {e}")
            print("Skipping original orjson benchmark")
        
        # Switch to our version
        print("\n" + "="*60)
        print("Switching to MODIFIED orjson (subinterpreter-compatible)")
        print("="*60)
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "orjson"], 
                      capture_output=True, check=False)
        wheels = glob.glob("target/wheels/orjson*.whl")
        if wheels:
            subprocess.run([sys.executable, "-m", "pip", "install", "--user", wheels[0]], 
                          capture_output=True, check=False)
        else:
            print("ERROR: Could not find wheel file. Building...")
            subprocess.run([sys.executable, "-m", "maturin", "build", "--release"], 
                          check=False)
            wheels = glob.glob("target/wheels/orjson*.whl")
            if wheels:
                subprocess.run([sys.executable, "-m", "pip", "install", "--user", wheels[0]], 
                              capture_output=True, check=False)
        
        # Clear module cache and reimport
        if 'orjson' in sys.modules:
            del sys.modules['orjson']
        import orjson as orjson_modified
        
        # Benchmark with random objects
        print("\nGenerating fresh random objects for each iteration...")
        
        # Serialization benchmark
        serialize_start = time.perf_counter()
        total_serialized_size = 0
        for _ in range(random_iterations):
            test_obj = generate_random_json_object()
            serialized = orjson_modified.dumps(test_obj)
            total_serialized_size += len(serialized)
        serialize_time = time.perf_counter() - serialize_start
        
        # Deserialization benchmark
        test_objects_serialized = []
        for _ in range(random_iterations):
            test_obj = generate_random_json_object()
            test_objects_serialized.append(orjson_modified.dumps(test_obj))
        
        deserialize_start = time.perf_counter()
        for serialized in test_objects_serialized:
            _ = orjson_modified.loads(serialized)
        deserialize_time = time.perf_counter() - deserialize_start
        
        # Round-trip benchmark
        roundtrip_start = time.perf_counter()
        for _ in range(random_iterations):
            test_obj = generate_random_json_object()
            serialized = orjson_modified.dumps(test_obj)
            _ = orjson_modified.loads(serialized)
        roundtrip_time = time.perf_counter() - roundtrip_start
        
        serialize_ops_per_sec = random_iterations / serialize_time
        deserialize_ops_per_sec = random_iterations / deserialize_time
        roundtrip_ops_per_sec = random_iterations / roundtrip_time
        
        print(f"\nSerialization:")
        print(f"  Time: {serialize_time:.4f}s")
        print(f"  Operations/sec: {serialize_ops_per_sec:,.0f}")
        print(f"  Avg time per op: {(serialize_time/random_iterations)*1e6:.2f}μs")
        
        print(f"\nDeserialization:")
        print(f"  Time: {deserialize_time:.4f}s")
        print(f"  Operations/sec: {deserialize_ops_per_sec:,.0f}")
        print(f"  Avg time per op: {(deserialize_time/random_iterations)*1e6:.2f}μs")
        
        print(f"\nRound-trip:")
        print(f"  Time: {roundtrip_time:.4f}s")
        print(f"  Operations/sec: {roundtrip_ops_per_sec:,.0f}")
        print(f"  Avg time per op: {(roundtrip_time/random_iterations)*1e6:.2f}μs")
        
        print(f"\nAvg serialized size: {total_serialized_size / random_iterations:.0f} bytes")
        
        mod_result = {
            'name': 'Modified orjson (subinterpreter-compatible) - Random',
            'serialize_time': serialize_time,
            'deserialize_time': deserialize_time,
            'roundtrip_time': roundtrip_time,
            'serialize_ops_per_sec': serialize_ops_per_sec,
            'deserialize_ops_per_sec': deserialize_ops_per_sec,
            'roundtrip_ops_per_sec': roundtrip_ops_per_sec,
            'serialized_size': total_serialized_size // random_iterations
        }
        
        # Comparison for random objects
        if orig_result is not None:
            print(f"\n{'='*60}")
            print("PERFORMANCE COMPARISON - Random Objects")
            print(f"{'='*60}")
            
            print(f"\nSerialization:")
            serialize_diff = ((mod_result['serialize_time'] - orig_result['serialize_time']) / orig_result['serialize_time']) * 100
            print(f"  Original:  {orig_result['serialize_ops_per_sec']:,.0f} ops/sec")
            print(f"  Modified:  {mod_result['serialize_ops_per_sec']:,.0f} ops/sec")
            if serialize_diff > 0:
                print(f"  Modified is {serialize_diff:.2f}% slower")
            else:
                print(f"  Modified is {abs(serialize_diff):.2f}% faster")
            
            print(f"\nDeserialization:")
            deserialize_diff = ((mod_result['deserialize_time'] - orig_result['deserialize_time']) / orig_result['deserialize_time']) * 100
            print(f"  Original:  {orig_result['deserialize_ops_per_sec']:,.0f} ops/sec")
            print(f"  Modified:  {mod_result['deserialize_ops_per_sec']:,.0f} ops/sec")
            if deserialize_diff > 0:
                print(f"  Modified is {deserialize_diff:.2f}% slower")
            else:
                print(f"  Modified is {abs(deserialize_diff):.2f}% faster")
            
            print(f"\nRound-trip:")
            roundtrip_diff = ((mod_result['roundtrip_time'] - orig_result['roundtrip_time']) / orig_result['roundtrip_time']) * 100
            print(f"  Original:  {orig_result['roundtrip_ops_per_sec']:,.0f} ops/sec")
            print(f"  Modified:  {mod_result['roundtrip_ops_per_sec']:,.0f} ops/sec")
            if roundtrip_diff > 0:
                print(f"  Modified is {roundtrip_diff:.2f}% slower")
            else:
                print(f"  Modified is {abs(roundtrip_diff):.2f}% faster")
            
            # Overall assessment
            max_diff = max(abs(serialize_diff), abs(deserialize_diff), abs(roundtrip_diff))
            avg_diff = (serialize_diff + deserialize_diff + roundtrip_diff) / 3
            
            print(f"\n{'='*60}")
            print(f"Overall Assessment - Random Objects:")
            print(f"  Average difference: {avg_diff:+.2f}%")
            print(f"  Maximum difference: {max_diff:.2f}%")
            
            if abs(avg_diff) < 2:
                print(f"\n✅ Performance is excellent - within 2% of original!")
            elif abs(avg_diff) < 5:
                print(f"\n✅ Performance is very good - within 5% of original!")
            elif abs(avg_diff) < 10:
                print(f"\n⚠️  Performance is acceptable - within 10% of original")
            else:
                if avg_diff > 0:
                    print(f"\n❌ Performance is {avg_diff:.2f}% slower - may need optimization")
                else:
                    print(f"\n✅ Performance is {abs(avg_diff):.2f}% faster - excellent improvement!")
        return
    
    # Original benchmark
    print("Creating complex test structure...")
    test_data = create_complex_structure()
    print(f"Test structure created:")
    print(f"  - {len(test_data['persons'])} persons")
    print(f"  - Nested dictionaries up to 4 levels deep")
    print(f"  - Mixed data types (strings, numbers, booleans, lists, dicts)")
    print(f"  - Datetime strings")
    print(f"  - UUIDs")
    
    results = []
    iterations = 10000
    
    # Benchmark original orjson
    print("\n" + "="*60)
    print("Testing ORIGINAL orjson (PyPI 3.11.4)")
    print("="*60)
    try:
        # Clear any cached imports
        if 'orjson' in sys.modules:
            del sys.modules['orjson']
        import orjson as orjson_original
        result = benchmark_orjson(orjson_original, "Original orjson (PyPI 3.11.4)", test_data, iterations)
        results.append(result)
    except Exception as e:
        print(f"Error loading original orjson: {e}")
        print("Skipping original orjson benchmark")
    
    # Uninstall original and install our version
    print("\n" + "="*60)
    print("Switching to MODIFIED orjson (subinterpreter-compatible)")
    print("="*60)
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "orjson"], 
                   capture_output=True, check=False)
    # Find the wheel file
    wheels = glob.glob("target/wheels/orjson*.whl")
    if wheels:
        subprocess.run([sys.executable, "-m", "pip", "install", "--user", wheels[0]], 
                      capture_output=True, check=False)
    else:
        print("ERROR: Could not find wheel file. Building...")
        subprocess.run([sys.executable, "-m", "maturin", "build", "--release"], 
                      check=False)
        wheels = glob.glob("target/wheels/orjson*.whl")
        if wheels:
            subprocess.run([sys.executable, "-m", "pip", "install", "--user", wheels[0]], 
                          capture_output=True, check=False)
    
    # Clear module cache and reimport
    if 'orjson' in sys.modules:
        del sys.modules['orjson']
    import orjson as orjson_modified
    
    result = benchmark_orjson(orjson_modified, "Modified orjson (subinterpreter-compatible)", 
                             test_data, iterations)
    results.append(result)
    
    # Comparison
    if len(results) == 2:
        print(f"\n{'='*60}")
        print("PERFORMANCE COMPARISON")
        print(f"{'='*60}")
        
        orig = results[0]
        mod = results[1]
        
        print(f"\nSerialization:")
        serialize_diff = ((mod['serialize_time'] - orig['serialize_time']) / orig['serialize_time']) * 100
        print(f"  Original:  {orig['serialize_ops_per_sec']:,.0f} ops/sec")
        print(f"  Modified:  {mod['serialize_ops_per_sec']:,.0f} ops/sec")
        if serialize_diff > 0:
            print(f"  Modified is {serialize_diff:.2f}% slower")
        else:
            print(f"  Modified is {abs(serialize_diff):.2f}% faster")
        
        print(f"\nDeserialization:")
        deserialize_diff = ((mod['deserialize_time'] - orig['deserialize_time']) / orig['deserialize_time']) * 100
        print(f"  Original:  {orig['deserialize_ops_per_sec']:,.0f} ops/sec")
        print(f"  Modified:  {mod['deserialize_ops_per_sec']:,.0f} ops/sec")
        if deserialize_diff > 0:
            print(f"  Modified is {deserialize_diff:.2f}% slower")
        else:
            print(f"  Modified is {abs(deserialize_diff):.2f}% faster")
        
        print(f"\nRound-trip:")
        roundtrip_diff = ((mod['roundtrip_time'] - orig['roundtrip_time']) / orig['roundtrip_time']) * 100
        print(f"  Original:  {orig['roundtrip_ops_per_sec']:,.0f} ops/sec")
        print(f"  Modified:  {mod['roundtrip_ops_per_sec']:,.0f} ops/sec")
        if roundtrip_diff > 0:
            print(f"  Modified is {roundtrip_diff:.2f}% slower")
        else:
            print(f"  Modified is {abs(roundtrip_diff):.2f}% faster")
        
        # Overall assessment
        max_diff = max(abs(serialize_diff), abs(deserialize_diff), abs(roundtrip_diff))
        avg_diff = (serialize_diff + deserialize_diff + roundtrip_diff) / 3
        
        print(f"\n{'='*60}")
        print(f"Overall Assessment:")
        print(f"  Average difference: {avg_diff:+.2f}%")
        print(f"  Maximum difference: {max_diff:.2f}%")
        
        if abs(avg_diff) < 2:
            print(f"\n✅ Performance is excellent - within 2% of original!")
        elif abs(avg_diff) < 5:
            print(f"\n✅ Performance is very good - within 5% of original!")
        elif abs(avg_diff) < 10:
            print(f"\n⚠️  Performance is acceptable - within 10% of original")
        else:
            if avg_diff > 0:
                print(f"\n❌ Performance is {avg_diff:.2f}% slower - may need optimization")
            else:
                print(f"\n✅ Performance is {abs(avg_diff):.2f}% faster - excellent improvement!")


if __name__ == "__main__":
    main()
